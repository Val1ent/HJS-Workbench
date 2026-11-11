/********************************** (C) COPYRIGHT *******************************
* File Name          : dma_capture.c
* Author             : WCH
* Version            : V1.0.0
* Date               : 2026/11/10
* Description        : Timer-triggered DMA capture of the 8-channel GPIOD input
*                      register.
*
*                      TIM2 update events trigger DMA1_Channel1, peripheral
*                      source GPIOD->INDR, byte width, into circular RAM
*                      buffers. No CPU instruction runs per sample, so the
*                      capture time base cannot be disturbed by other
*                      interrupt load.
*
*                      Two milestones share this file:
*                      B1 - the channel boots in single-buffer mode; transfer
*                           complete (TC) interrupts prove the hardware trigger
*                           and the data authenticity while the buffer wraps.
*                      B2 - after the first full block, the main loop promotes
*                           the channel to double-buffer mode (Memory0 /
*                           Memory1); every TC then marks the just-completed
*                           block ready and the main loop sends it over USB.
*
*                      Supported rates: 10000 / 100000 / 500000 / 1000000 Hz.
*                      TIM2 prescaler is fixed at 99 (1 MHz counter clock) for
*                      the 10k/100k/500k tiers; the 1M tier uses PSC=24 with
*                      ARR=3 (4 MHz tick / 4 counts = exactly 1 MHz) because
*                      ARR=0 provably produces no update events on this
*                      silicon.
*
*                      TIM3 runs a fixed 10 kHz time base for the signal
*                      generator, fully independent of the sampling rate.
*********************************************************************************
* Copyright (c) 2025 Nanjing Qinheng Microelectronics Co., Ltd.
* Attention: This software (modified or not) and binary are used for
* microcontroller manufactured by Nanjing Qinheng Microelectronics.
*******************************************************************************/

#include "dma_capture.h"
#include "hardware.h"

/* One capture block: 1000 bytes, the low byte of GPIOD->INDR per sample */
#define CAP_BLOCK_LEN       1000u

#define CAP_RATE_10K        10000u
#define CAP_RATE_100K       100000u
#define CAP_RATE_500K       500000u
#define CAP_RATE_1M         1000000u

/* TIM2/TIM3 prescaler for the 10k/100k/500k tiers and the TIM3 signal
   time base: 100 MHz / (99 + 1) = 1 MHz counter clock, 1 tick = 1 us.
   The 1M tier overrides this (see tim2_base_config). */
#define CAP_TIM_PSC         99u

/* DMAMUX request number of the TIM2 update event (1-based, RM Table 10-2).
   DMA_MuxChannelConfig stores request - 1 in the 7-bit field, so pass 12;
   do not compensate when the register reads back 11. */
#define CAP_DMAMUX_TIM2_UP  12u

/* DMA1_Channel1 CFGR bit 16 (CT): current write target in double-buffer mode */
#define CAP_CFGR_CT         ((uint32_t)0x00010000)

/* Capture phases */
#define CAP_PHASE_SINGLE    0u
#define CAP_PHASE_DOUBLE    1u

/* Block indices */
#define CAP_BLK0            0u
#define CAP_BLK1            1u
#define CAP_BLK_NONE        0xFFu

/* Block states shared by the DMA interrupt and the main loop */
#define CAP_BLK_FREE        0u
#define CAP_BLK_READY       1u
#define CAP_BLK_TAKEN       2u

static uint8_t cap_buf0[CAP_BLOCK_LEN] __attribute__((aligned(4)));
static uint8_t cap_buf1[CAP_BLOCK_LEN] __attribute__((aligned(4)));

static volatile uint8_t  cap_phase;      /* CAP_PHASE_SINGLE then CAP_PHASE_DOUBLE */
static volatile uint8_t  blk_state0;     /* CAP_BLK_FREE / READY / TAKEN */
static volatile uint8_t  blk_state1;
static volatile uint8_t  taken_blk;      /* block currently held by the main loop */
static volatile uint32_t tc_count;       /* transfer-complete count, all phases */
static volatile uint32_t te_count;       /* DMA transfer-error count */
static volatile uint32_t ovf_count;      /* blocks overwritten before release */
static volatile uint32_t reject_count;   /* rejected rate commands */
static volatile uint32_t cur_rate;

void DMA1_Channel1_IRQHandler(void)__attribute__((interrupt("WCH-Interrupt-fast")));
void TIM3_IRQHandler(void)__attribute__((interrupt("WCH-Interrupt-fast")));

/* Return the rate when supported, 0 when not */
static uint32_t rate_valid(uint32_t sample_rate)
{
    if(sample_rate == CAP_RATE_10K)  return CAP_RATE_10K;
    if(sample_rate == CAP_RATE_100K) return CAP_RATE_100K;
    if(sample_rate == CAP_RATE_500K) return CAP_RATE_500K;
    if(sample_rate == CAP_RATE_1M)   return CAP_RATE_1M;
    return 0;
}

/* TIM2 time base: PSC fixed at 99, ARR selects the rate.
   Exception: the 1M tier. Measured on silicon (register dump via SWD):
   with ARR=0 the counter stays at 0 and the update flag never sets, so no
   DMA trigger ever fires. The 1M tier therefore uses PSC=24 -> 4 MHz tick
   and ARR=3 -> exactly 1 MHz. Do not change these back to ARR=0, and do not
   use PSC=99 with ARR=1 (that would run at 500 kHz). */
static void tim2_base_config(uint32_t rate)
{
    TIM_TimeBaseInitTypeDef t = {0};
    if(rate == CAP_RATE_1M)
    {
        t.TIM_Period    = 3u;
        t.TIM_Prescaler = 24u;
    }
    else
    {
        t.TIM_Period    = (uint16_t)((1000000u / rate) - 1u);
        t.TIM_Prescaler = CAP_TIM_PSC;
    }
    t.TIM_ClockDivision = TIM_CKD_DIV1;
    t.TIM_CounterMode   = TIM_CounterMode_Up;
    TIM_TimeBaseInit(TIM2, &t);
}

/* DMA1_Channel1 register set; call only while the channel is disabled.
   start_mem1 selects Memory1 as the first write target in double-buffer
   mode (used to keep an in-flight block intact across a rate switch). */
static void dma_channel_config(uint8_t double_buf, uint8_t start_mem1)
{
    DMA_InitTypeDef d = {0};
    d.DMA_PeripheralBaseAddr    = (uint32_t)(&GPIOD->INDR);
    d.DMA_Memory0BaseAddr       = (uint32_t)cap_buf0;
    d.DMA_DIR                   = DMA_DIR_PeripheralSRC;
    d.DMA_BufferSize            = CAP_BLOCK_LEN;
    d.DMA_PeripheralInc         = DMA_PeripheralInc_Disable;
    d.DMA_MemoryInc             = DMA_MemoryInc_Enable;
    d.DMA_PeripheralDataSize    = DMA_PeripheralDataSize_Byte;
    d.DMA_MemoryDataSize        = DMA_MemoryDataSize_Byte;
    d.DMA_Mode                  = DMA_Mode_Circular;
    d.DMA_Priority              = DMA_Priority_VeryHigh;
    d.DMA_M2M                   = DMA_M2M_Disable;
    if(double_buf)
    {
        d.DMA_BufferMode            = DMA_DoubleBufferMode;
        d.DMA_Memory1BaseAddr       = (uint32_t)cap_buf1;
        d.DMA_DoubleBuffer_StartMemory = start_mem1 ? DMA_DoubleBufferMode_Memory_1
                                                    : DMA_DoubleBufferMode_Memory_0;
    }
    else
    {
        d.DMA_BufferMode = DMA_SingleBufferMode;
    }
    DMA_Init(DMA1_Channel1, &d);
}

/* Full channel surgery: mask the NVIC IRQ, stop the channel, DeInit,
   reconfigure, re-arm the interrupts and clear the flags twice (before and
   after the channel is enabled again). Disabling a channel mid-transfer can
   raise a spurious transfer-error flag; the double clear inside the masked
   window keeps such artifacts out of the error counter. The caller must
   have stopped TIM2 first so no update event races the reconfiguration. */
static void dma_reconfig(uint8_t double_buf, uint8_t start_mem1)
{
    NVIC_DisableIRQ(DMA1_Channel1_IRQn);
    DMA_Cmd(DMA1_Channel1, DISABLE);
    DMA_DeInit(DMA1_Channel1);
    dma_channel_config(double_buf, start_mem1);
    DMA_MuxChannelConfig(DMA_MuxChannel1, CAP_DMAMUX_TIM2_UP);
    DMA_ITConfig(DMA1_Channel1, DMA_IT_TC, ENABLE);
    DMA_ITConfig(DMA1_Channel1, DMA_IT_TE, ENABLE);
    DMA_ClearFlag(DMA1, DMA1_FLAG_TC1 | DMA1_FLAG_TE1);
    DMA_Cmd(DMA1_Channel1, ENABLE);
    DMA_ClearFlag(DMA1, DMA1_FLAG_TC1 | DMA1_FLAG_TE1);
    NVIC_EnableIRQ(DMA1_Channel1_IRQn);
}

/*********************************************************************
 * @fn      Capture_HW_Init
 *
 * @brief   DMA1 clock, DMAMUX, DMA1_Channel1 and the TIM2 sampling timer.
 *          Boots in single-buffer mode; the main loop promotes the channel
 *          to double-buffer mode after the first full block (milestone B2).
 *
 * @param   sample_rate - 10000 / 100000 / 500000 / 1000000
 *
 * @return  none
 */
void Capture_HW_Init(uint32_t sample_rate)
{
    uint32_t rate = rate_valid(sample_rate);
    if(rate == 0) rate = CAP_RATE_10K;

    cap_phase    = CAP_PHASE_SINGLE;
    blk_state0   = CAP_BLK_FREE;
    blk_state1   = CAP_BLK_FREE;
    taken_blk    = CAP_BLK_NONE;
    tc_count     = 0;
    te_count     = 0;
    ovf_count    = 0;
    reject_count = 0;
    cur_rate     = 0;

    /* DMA1 clock: enabled by RCC_Configuration, confirm explicitly */
    RCC_HBPeriphClockCmd(RCC_HBPeriph_DMA1, ENABLE);

    /* TIM2 sampling timer: update events trigger DMA only, no NVIC IRQ.
       The TIM2 clock stays enabled in RCC_Configuration. */
    TIM_DeInit(TIM2);
    tim2_base_config(rate);
    TIM_ClearFlag(TIM2, TIM_FLAG_Update);
    TIM_DMACmd(TIM2, TIM_DMA_Update, ENABLE);

    /* Single-buffer milestone (B1) runs first */
    dma_reconfig(0, 0);

    TIM_Cmd(TIM2, ENABLE);
    cur_rate = rate;
}

/* Promote the channel to double-buffer mode (milestone B2). Runs in
   main-loop context after the single-buffer phase produced its first full
   block, so the B1 trigger proof precedes the tear-free B2 stream. */
static void capture_promote_double(void)
{
    TIM_Cmd(TIM2, DISABLE);
    dma_reconfig(1, 0);
    blk_state0 = CAP_BLK_FREE;
    blk_state1 = CAP_BLK_FREE;
    taken_blk  = CAP_BLK_NONE;
    TIM_ClearFlag(TIM2, TIM_FLAG_Update);
    TIM_Cmd(TIM2, ENABLE);
    cap_phase = CAP_PHASE_DOUBLE;
    printf("CAP: single-buffer phase done (tc=%lu), double buffer active\n", tc_count);
}

/*********************************************************************
 * @fn      Capture_SetRate
 *
 * @brief   Runtime sample-rate switch. Rejects unsupported rates without
 *          touching any hardware state.
 *
 * @param   sample_rate - 10000 / 100000 / 500000 / 1000000
 *
 * @return  0 on success, -1 on an unsupported rate
 */
int Capture_SetRate(uint32_t sample_rate)
{
    uint32_t rate = rate_valid(sample_rate);
    if(rate == 0)
    {
        reject_count++;
        return -1;
    }

    /* Stop the timer before any register surgery so no update event races
       the channel reconfiguration */
    TIM_Cmd(TIM2, DISABLE);
    TIM_DeInit(TIM2);
    tim2_base_config(rate);
    TIM_ClearFlag(TIM2, TIM_FLAG_Update);
    TIM_DMACmd(TIM2, TIM_DMA_Update, ENABLE);

    dma_reconfig(cap_phase == CAP_PHASE_DOUBLE,
                 cap_phase == CAP_PHASE_DOUBLE && taken_blk == CAP_BLK0);

    /* A block still being sent keeps its TAKEN state; stale ready data is
       discarded so the stream switches to the new rate cleanly */
    if(blk_state0 != CAP_BLK_TAKEN) blk_state0 = CAP_BLK_FREE;
    if(blk_state1 != CAP_BLK_TAKEN) blk_state1 = CAP_BLK_FREE;

    TIM_Cmd(TIM2, ENABLE);
    cur_rate = rate;
    return 0;
}

/*********************************************************************
 * @fn      Capture_TakeBlock
 *
 * @brief   Return a full block that is safe to send, or NULL when no full
 *          block is available. The first call after the single-buffer
 *          milestone promotes the channel to double-buffer mode.
 *
 * @param   out_len - set to the block length on success, 0 otherwise
 *
 * @return  pointer to the block, or NULL
 */
const uint8_t* Capture_TakeBlock(uint16_t *out_len)
{
    if(out_len != 0) *out_len = 0;

    if(cap_phase == CAP_PHASE_SINGLE)
    {
        if(tc_count >= 1) capture_promote_double();
        return 0;
    }

    if(blk_state0 == CAP_BLK_READY)
    {
        blk_state0 = CAP_BLK_TAKEN;
        taken_blk = CAP_BLK0;
        if(out_len != 0) *out_len = CAP_BLOCK_LEN;
        return cap_buf0;
    }
    if(blk_state1 == CAP_BLK_READY)
    {
        blk_state1 = CAP_BLK_TAKEN;
        taken_blk = CAP_BLK1;
        if(out_len != 0) *out_len = CAP_BLOCK_LEN;
        return cap_buf1;
    }
    return 0;
}

/*********************************************************************
 * @fn      Capture_ReleaseBlock
 *
 * @brief   Hand the last taken block back to the DMA for reuse.
 *
 * @return  none
 */
void Capture_ReleaseBlock(void)
{
    if(taken_blk == CAP_BLK0) blk_state0 = CAP_BLK_FREE;
    else if(taken_blk == CAP_BLK1) blk_state1 = CAP_BLK_FREE;
    taken_blk = CAP_BLK_NONE;
}

uint32_t Capture_OverflowCount(void)
{
    return ovf_count;
}

uint32_t Capture_ErrorCount(void)
{
    return te_count;
}

uint32_t Capture_CurrentRate(void)
{
    return cur_rate;
}

uint32_t Capture_RejectCount(void)
{
    return reject_count;
}

/*********************************************************************
 * @fn      Signal_Timer_Init
 *
 * @brief   TIM3 fixed 10 kHz time base for the signal generator, fully
 *          independent of the TIM2 sampling rate.
 *
 * @return  none
 */
void Signal_Timer_Init(void)
{
    TIM_TimeBaseInitTypeDef t = {0};

    RCC_HB1PeriphClockCmd(RCC_HB1Periph_TIM3, ENABLE);
    TIM_DeInit(TIM3);
    t.TIM_Period        = 99u;
    t.TIM_Prescaler     = CAP_TIM_PSC;
    t.TIM_ClockDivision = TIM_CKD_DIV1;
    t.TIM_CounterMode   = TIM_CounterMode_Up;
    TIM_TimeBaseInit(TIM3, &t);
    TIM_ClearFlag(TIM3, TIM_FLAG_Update);
    TIM_ITConfig(TIM3, TIM_IT_Update, ENABLE);
    NVIC_EnableIRQ(TIM3_IRQn);
    TIM_Cmd(TIM3, ENABLE);
}

/*********************************************************************
 * @fn      DMA1_Channel1_IRQHandler
 *
 * @brief   Count transfer completes and errors, and in double-buffer mode
 *          mark the just-completed block ready. Flags, counters and block
 *          state only: no USB send, no big copies, no printf in here.
 *
 * @return  none
 */
void DMA1_Channel1_IRQHandler(void)
{
    if(DMA_GetITStatus(DMA1, DMA1_IT_TC1))
    {
        DMA_ClearITPendingBit(DMA1, DMA1_IT_TC1);
        tc_count++;
        if(cap_phase == CAP_PHASE_DOUBLE)
        {
            uint8_t done;
            /* CT=0: Memory0 is the current write target, Memory1 just
               completed. CT=1: Memory1 is the target, Memory0 completed. */
            done = (DMA1_Channel1->CFGR & CAP_CFGR_CT) ? CAP_BLK0 : CAP_BLK1;
            if(done == CAP_BLK0)
            {
                if(blk_state0 == CAP_BLK_FREE) blk_state0 = CAP_BLK_READY;
                else ovf_count++;
            }
            else
            {
                if(blk_state1 == CAP_BLK_FREE) blk_state1 = CAP_BLK_READY;
                else ovf_count++;
            }

            /* The other block is now the DMA write target: if it still
               holds ready data that the main loop never consumed, that
               data is lost and counted, and the block is freed so the
               main loop can never send half-overwritten data. */
            if(done == CAP_BLK0)
            {
                if(blk_state1 == CAP_BLK_READY)
                {
                    ovf_count++;
                    blk_state1 = CAP_BLK_FREE;
                }
            }
            else
            {
                if(blk_state0 == CAP_BLK_READY)
                {
                    ovf_count++;
                    blk_state0 = CAP_BLK_FREE;
                }
            }
        }
    }
    if(DMA_GetITStatus(DMA1, DMA1_IT_TE1))
    {
        DMA_ClearITPendingBit(DMA1, DMA1_IT_TE1);
        te_count++;
    }
}

/*********************************************************************
 * @fn      TIM3_IRQHandler
 *
 * @brief   Fixed 10 kHz tick for the signal generator. The ISR only clears
 *          the pending bit and drives the existing Signal_Tick state
 *          machine; its timing does not depend on the sampling rate.
 *
 * @return  none
 */
void TIM3_IRQHandler(void)
{
    if(TIM_GetITStatus(TIM3, TIM_IT_Update))
    {
        TIM_ClearITPendingBit(TIM3, TIM_IT_Update);
        Signal_Tick();
    }
}
