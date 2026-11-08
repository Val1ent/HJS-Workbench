/********************************** (C) COPYRIGHT  *******************************
* Logic analyzer: GPIO sampling runs inside the TIM2 interrupt (ring buffer); the main loop only sends over USB
* This way sampling is never interrupted and no points are lost while a USB send blocks; the time axis stays accurate
* Self-test signal source: software-emulated UART, PA15 plain push-pull, 1000 bps, A15->D0
* Add a UART decoder (1000-8N1) in PulseView to decode "Hello CH32!"
*******************************************************************************/
#include "hardware.h"
#include "ch32h417_usbfs_device.h"

#define BATCH_POINTS 1000
static uint8_t batch_buf[BATCH_POINTS];

/* ===== Capture ring buffer (written in ISR / read in main loop) ===== */
#define RING_SIZE 2048   /* must be a power of two; holds samples while a USB send blocks (task-5 clean value) */
static uint8_t  cap_ring[RING_SIZE];
static volatile uint16_t ring_head = 0;
static volatile uint16_t ring_tail = 0;

/* ===== Software UART signal source (PA15 / 1000 bps) ===== */
static const char sig_msg[] = "Hello CH32!\r\n";
#define SIG_LEN         (sizeof(sig_msg) - 1)
#define TICKS_PER_BIT   10    /* 100us * 10 = 1ms/bit -> 1000bps @10kHz */
#define BITS_PER_FRAME  10    /* start bit + 8 data bits + stop bit */

static volatile uint8_t sig_active = 0;
static uint8_t sig_char;
static uint8_t sig_bit;
static uint8_t sig_tick;
static uint16_t sig_restart_cnt;   /* counts while idle; resends when the count is reached */

/* ===== Signal generator mode: 0=software UART, 1=square wave, 2=PWM, 3=burst, 4=forced level ===== */
volatile uint8_t sig_mode = 0;
volatile uint16_t sig_square_div = 5;  /* ticks per square half period: freq=10000/(2*div), div=5 -> 1 kHz */
static uint16_t sig_square_cnt = 0;
volatile uint8_t last_cmd = 0;   /* last valid command: 0=UART, 1=square, 2=PWM, 3=burst, 4=forced level; empty packets follow it */

/* PWM: period = sig_pwm_div ticks, high for sig_pwm_duty ticks (1..div-1).
   The 100us tick quantizes the duty; div=5 gives 1 kHz with 20% steps. */
volatile uint16_t sig_pwm_div = 5;
volatile uint16_t sig_pwm_duty = 3;
static uint16_t sig_pwm_cnt = 0;

/* Burst: exactly sig_burst_total full periods (div ticks high + div ticks
   low each), then the line is held high. 0 periods holds high immediately. */
volatile uint16_t sig_burst_div = 5;
volatile uint16_t sig_burst_total = 0;
static uint16_t sig_burst_cnt = 0;
static uint8_t  sig_burst_half = 0;   /* 0=high half, 1=low half */

/* Forced level: sig_mode=4 keeps PA15 at sig_force_level. */
volatile uint8_t sig_force_level = 1;

/* ===== PC command reception (USB endpoint 2) ===== */
__attribute__((aligned(4))) uint8_t cmd_dma_buf[64];   /* endpoint 2 DMA landing buffer */
static char cmd_line[32];
static uint8_t cmd_len = 0;

static void USB_SendBuf(const uint8_t *data, uint16_t len)
{
    uint16_t off = 0;
    while(off < len)
    {
        uint16_t chunk = len - off;
        if(chunk > DEF_USBD_ENDP3_SIZE) chunk = DEF_USBD_ENDP3_SIZE;
        while((USBFSD->UEP3_TX_CTRL & USBFS_UEP_T_RES_MASK) != USBFS_UEP_T_RES_NAK);
        memcpy(USBFS_EP3_Buf, data + off, chunk);
        USBFSD->UEP3_TX_LEN = chunk;
        USBFSD->UEP3_TX_CTRL = (USBFSD->UEP3_TX_CTRL & ~USBFS_UEP_T_RES_MASK)
                             | USBFS_UEP_T_RES_ACK;
        off += chunk;
    }
}

/* Capture pins PD0-7: pull-up inputs */
static void Capture_GPIO_Init(void)
{
    GPIO_InitTypeDef g = {0};
    RCC_HB2PeriphClockCmd(RCC_HB2Periph_GPIOD, ENABLE);
    g.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 | GPIO_Pin_3
               | GPIO_Pin_4 | GPIO_Pin_5 | GPIO_Pin_6 | GPIO_Pin_7;
    g.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOD, &g);
}

/* Software UART pin: PA15 plain push-pull output; PC6 diagnostic output */
static void Signal_Init(void)
{
    GPIO_InitTypeDef g = {0};

    RCC_HB2PeriphClockCmd(RCC_HB2Periph_GPIOA, ENABLE);
    g.GPIO_Pin   = GPIO_Pin_15;
    g.GPIO_Speed = GPIO_Speed_Very_High;
    g.GPIO_Mode  = GPIO_Mode_Out_PP;
    GPIO_Init(GPIOA, &g);

    GPIOA->BSHR = GPIO_Pin_15;   /* idle high */
    sig_active = 0;

    /* Diagnostic: PC6 push-pull output, toggles once per OUT packet */
    RCC_HB2PeriphClockCmd(RCC_HB2Periph_GPIOC, ENABLE);
    g.GPIO_Pin   = GPIO_Pin_6;
    g.GPIO_Speed = GPIO_Speed_Very_High;
    g.GPIO_Mode  = GPIO_Mode_Out_PP;
    GPIO_Init(GPIOC, &g);
    GPIOC->BCR = GPIO_Pin_6;
}

static void set_line(uint8_t v)
{
    if(v) GPIOA->BSHR = GPIO_Pin_15;
    else  GPIOA->BCR  = GPIO_Pin_15;
}

void Signal_Start(void)
{
    sig_char   = 0;
    sig_bit    = 0;
    sig_tick   = 0;
    sig_active = 1;
    set_line(0);   /* start bit */
}

void Signal_Tick(void)
{
    /* Forced-level mode: the command already set PA15; nothing to do */
    if(sig_mode == 4)
    {
        return;
    }

    /* Burst mode: output exactly sig_burst_total full periods, then hold
       the line high. Every branch is a bounded counter/compare. */
    if(sig_mode == 3)
    {
        if(sig_burst_total == 0)
        {
            set_line(1);
            return;
        }
        if(sig_burst_div == 0) sig_burst_div = 1;
        sig_burst_cnt++;
        if(sig_burst_cnt >= sig_burst_div)
        {
            sig_burst_cnt = 0;
            sig_burst_half ^= 1;
            set_line(sig_burst_half ? 0 : 1);
            if(sig_burst_half == 0)
            {
                /* A full period (high half + low half) completed */
                sig_burst_total--;
                if(sig_burst_total == 0) set_line(1);
            }
        }
        return;
    }

    /* PWM mode: compare the tick counter against the duty ticks. The
       100us tick quantizes the duty resolution. */
    if(sig_mode == 2)
    {
        if(sig_pwm_div < 2) sig_pwm_div = 2;
        if(sig_pwm_duty == 0 || sig_pwm_duty >= sig_pwm_div)
            sig_pwm_duty = sig_pwm_div / 2;
        sig_pwm_cnt++;
        if(sig_pwm_cnt >= sig_pwm_div) sig_pwm_cnt = 0;
        set_line((sig_pwm_cnt < sig_pwm_duty) ? 1 : 0);
        return;
    }

    /* Square-wave mode: toggle PA15 after div ticks, freq = 10000/(2*div) */
    if(sig_mode == 1)
    {
        if(sig_square_div == 0) sig_square_div = 1;
        sig_square_cnt++;
        if(sig_square_cnt >= sig_square_div)
        {
            sig_square_cnt = 0;
            GPIOA->OUTDR ^= GPIO_Pin_15;
        }
        return;
    }

    if(!sig_active)
    {
        /* Idle: after 2000 ticks = 200 ms, resend once (aligned to the interrupt boundary) */
        sig_restart_cnt++;
        if(sig_restart_cnt >= 2000)
        {
            sig_restart_cnt = 0;
            Signal_Start();
        }
        return;
    }
    sig_restart_cnt = 0;

    sig_tick++;
    if(sig_tick < TICKS_PER_BIT) return;
    sig_tick = 0;

    sig_bit++;
    if(sig_bit >= BITS_PER_FRAME)
    {
        sig_char++;
        if(sig_char >= SIG_LEN)
        {
            sig_active = 0;
            set_line(1);
            return;
        }
        sig_bit = 0;
        set_line(0);
    }
    else if(sig_bit <= 8)
    {
        set_line(((uint8_t)sig_msg[sig_char] >> (sig_bit - 1)) & 0x01);
    }
    else
    {
        set_line(1);
    }
}

/* Called by the TIM2 interrupt every 100us: store a sample in the ring buffer */
void Capture_Tick(void)
{
    uint16_t next = (ring_head + 1) & (RING_SIZE - 1);
    if(next != ring_tail)   /* buffer not full */
    {
        cap_ring[ring_head] = (uint8_t)(GPIOD->INDR & 0x00FF);
        ring_head = next;
    }
}

/* Endpoint 2 received a packet (called in the USB ISR): process char by char immediately */
int Signal_HandleRx(const uint8_t *data, uint16_t len)
{
    uint16_t i;
    int ret = -1;
    for(i = 0; i < len; i++)
    {
        char c = (char)data[i];
        if(c == 'u' || c == 'U')
        {
            /* u switches to UART immediately, no newline wait */
            sig_mode = 0;
            Signal_Start();
            last_cmd = 0;
            cmd_len = 0;
            ret = 0;
        }
        else if(c == 'H' || c == 'h')
        {
            /* h forces the line high immediately */
            sig_mode = 4;
            sig_force_level = 1;
            sig_active = 0;
            set_line(1);
            last_cmd = 4;
            cmd_len = 0;
            ret = 4;
        }
        else if(c == 'L' || c == 'l')
        {
            /* l forces the line low immediately */
            sig_mode = 4;
            sig_force_level = 0;
            sig_active = 0;
            set_line(0);
            last_cmd = 4;
            cmd_len = 0;
            ret = 4;
        }
        else if(c == 'S' || c == 's')
        {
            /* S switches to square wave immediately (default 1 kHz), starts collecting digits; the frequency is fixed at the newline */
            cmd_len = 0;
            cmd_line[cmd_len++] = 'S';
            sig_mode = 1;
            sig_square_div = 5;
            last_cmd = 1;
            ret = 1;
        }
        else if(c == 'P' || c == 'p')
        {
            /* P switches to PWM immediately (default 1 kHz / 50%); the real values arrive with the newline */
            cmd_len = 0;
            cmd_line[cmd_len++] = 'P';
            sig_mode = 2;
            sig_pwm_div = 5;
            sig_pwm_duty = 3;
            sig_pwm_cnt = 0;
            last_cmd = 2;
            ret = 2;
        }
        else if(c == 'B' || c == 'b')
        {
            /* B starts collecting the burst command; with no counts yet it holds the line high (0 pulses) */
            cmd_len = 0;
            cmd_line[cmd_len++] = 'B';
            sig_mode = 3;
            sig_burst_div = 5;
            sig_burst_total = 0;
            sig_burst_cnt = 0;
            sig_burst_half = 0;
            set_line(1);
            last_cmd = 3;
            ret = 3;
        }
        else if((c >= '0' && c <= '9') || c == ',')
        {
            if(cmd_len > 0 && (cmd_line[0] == 'S' || cmd_line[0] == 'P' || cmd_line[0] == 'B')
               && cmd_len < sizeof(cmd_line) - 1)
                cmd_line[cmd_len++] = c;
        }
        else if(c == '\r' || c == '\n')
        {
            /* S/P/B command newline: parse and apply the full command */
            if(cmd_len > 0)
            {
                int r;
                cmd_line[cmd_len] = 0;
                r = Cmd_Parse(cmd_line);
                if(r >= 0)
                {
                    sig_mode = (uint8_t)r;
                    last_cmd = (uint8_t)r;
                    ret = r;
                }
                cmd_len = 0;
            }
        }
    }
    return ret;
}

/* Parse the two numbers of "X<num>,<num>": *a stops at the comma, *b
   follows it; numbers are 0 when absent. Returns 1 when a comma was seen. */
static uint8_t parse_two(const char *p, uint32_t *a, uint32_t *b)
{
    uint8_t comma = 0;
    *a = 0;
    *b = 0;
    while(*p >= '0' && *p <= '9') { *a = *a * 10 + (uint32_t)(*p - '0'); p++; }
    if(*p == ',')
    {
        comma = 1;
        p++;
        while(*p >= '0' && *p <= '9') { *b = *b * 10 + (uint32_t)(*p - '0'); p++; }
    }
    return comma;
}

/* Parse one command: returns the new signal mode (0=UART, 1=square,
   2=PWM, 3=burst, 4=forced level), or -1=invalid */
int Cmd_Parse(const char *line)
{
    if(line[0] == 'S' || line[0] == 's')
    {
        /* S<frequency Hz>: only sets div, e.g. S1000 -> div=5 */
        uint32_t f = 0;
        const char *p = line + 1;
        while(*p >= '0' && *p <= '9') { f = f * 10 + (uint32_t)(*p - '0'); p++; }
        if(f < 1) f = 1000;
        if(f > 5000) f = 5000;          /* max 5 kHz at 10 kHz sampling */
        sig_square_div = (uint16_t)(10000 / (2 * f));
        if(sig_square_div < 1) sig_square_div = 1;
        return 1;
    }
    if(line[0] == 'P' || line[0] == 'p')
    {
        /* P<frequency Hz>,<duty %>: duty resolution is one 100us tick */
        uint32_t f = 0, duty = 50, period;
        if(parse_two(line + 1, &f, &duty) == 0) duty = 50;
        if(f < 1) f = 1000;
        if(f > 5000) f = 5000;
        if(duty < 1) duty = 1;
        if(duty > 99) duty = 99;
        period = 10000 / f;
        if(period < 2) period = 2;
        sig_pwm_div = (uint16_t)period;
        sig_pwm_duty = (uint16_t)((duty * period + 50) / 100);
        if(sig_pwm_duty < 1) sig_pwm_duty = 1;
        if(sig_pwm_duty >= sig_pwm_div) sig_pwm_duty = (uint16_t)(sig_pwm_div - 1);
        sig_pwm_cnt = 0;
        return 2;
    }
    if(line[0] == 'B' || line[0] == 'b')
    {
        /* B<frequency Hz>,<pulse count>: output exactly count full
           periods (high half + low half each), then hold the line high */
        uint32_t f = 0, count = 0;
        parse_two(line + 1, &f, &count);
        if(f < 1) f = 1000;
        if(f > 5000) f = 5000;
        if(count > 65535) count = 65535;
        sig_burst_div = (uint16_t)(10000 / (2 * f));
        if(sig_burst_div < 1) sig_burst_div = 1;
        sig_burst_total = (uint16_t)count;
        sig_burst_cnt = 0;
        sig_burst_half = 0;
        set_line(1);
        return 3;
    }
    if(line[0] == 'U' || line[0] == 'u')
    {
        sig_mode = 0;
        Signal_Start();
        return 0;
    }
    if(line[0] == 'H' || line[0] == 'h')
    {
        sig_force_level = 1;
        sig_active = 0;
        set_line(1);
        return 4;
    }
    if(line[0] == 'L' || line[0] == 'l')
    {
        sig_force_level = 0;
        sig_active = 0;
        set_line(0);
        return 4;
    }
    return -1;
}

void Hardware(void)
{
    uint16_t batch_cnt = 0;

    printf("Build Time: %s %s\n", __DATE__, __TIME__);

    RCC_Configuration();
    TIM2_Init();
    Capture_GPIO_Init();
    Signal_Init();

    printf("Signal SoftUART on PA15, 1000bps, msg=%s", sig_msg);

    USBFS_RCC_Init();
    USBFS_Device_Init(ENABLE);

    Signal_Start();

    while(1)
    {
        /* Take data from the ring buffer and send it in batches; a blocking USB send does not affect ISR sampling */
        while(ring_tail != ring_head)
        {
            batch_buf[batch_cnt++] = cap_ring[ring_tail];
            ring_tail = (ring_tail + 1) & (RING_SIZE - 1);

            if(batch_cnt >= BATCH_POINTS)
            {
                USB_SendBuf(batch_buf, BATCH_POINTS);
                batch_cnt = 0;
            }
        }
    }
}
