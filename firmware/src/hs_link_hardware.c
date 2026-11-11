/********************************** (C) COPYRIGHT *******************************
 * File Name          : hs_link_hardware.c
 * Author             : WCH
 * Version            : V1.0.0
 * Date               : 2025/05/26
 * Description        : Stage 16C USB High-Speed real-time capture stream for
 *                      HJS-Workbench.
 *
 *                      The High-Speed main loop: TIM2 update events trigger
 *                      DMA1_Channel1 to fill the double capture buffers, and
 *                      each full 1000-byte block is streamed over the USBHS
 *                      EP3 IN endpoint as 512 + 488 byte packets. EP2 OUT
 *                      feeds the shared command parser. The USBHS CDC device
 *                      runs on PB8/PB9 (USB3 Type-A D+/D-), freed by
 *                      disabling the SWJ remap, so runtime SWD debugging is
 *                      unavailable while this firmware runs.
 *********************************************************************************
 * Copyright (c) 2025 Nanjing Qinheng Microelectronics Co., Ltd.
 * Attention: This software (modified or not) and binary are used for
 * microcontroller manufactured by Nanjing Qinheng Microelectronics.
 *******************************************************************************/
#include "hardware.h"
#include "dma_capture.h"
#include "ch32h417_usbhs_device.h"

/* Peripheral clock setup lives in UART.c; declare it locally instead of
   including UART.h, which pulls in the Full-Speed device header whose
   endpoint macros collide with the High-Speed header above. */
uint8_t RCC_Configuration(void);

/*********************************************************************
 * @fn      Hardware
 *
 * @brief   Stage 16C real-time High-Speed stream: initialize the capture
 *          pipeline (DMA double buffer + TIM2 sampling), the TIM3 signal
 *          time base, the USBHS CDC device, then stream every full capture
 *          block over EP3 IN and report diagnostics on the debug UART.
 *
 * @return  none
 */
void Hardware(void)
{
    printf("Build Time: %s %s\n", __DATE__, __TIME__);
    printf("USBHS real-time capture stream on PB8/PB9\n");

    /* Peripheral clocks (debug UART, AFIO, TIM2, DMA1) */
    RCC_Configuration();

    /* Capture inputs PD0-7 and signal generator output PA15 */
    Capture_GPIO_Init();
    Signal_Init();

    /* Release PB8/PB9 from SWCLK/SWDIO for the USBHS D+/D- pins.
       From this point on, runtime SWD debugging is unavailable. */
    RCC_HB2PeriphClockCmd(RCC_HB2Periph_AFIO | RCC_HB2Periph_GPIOB, ENABLE);
    GPIO_PinRemapConfig(GPIO_Remap_SWJ_Disable, ENABLE);

    /* TIM2-triggered DMA double-buffer capture at 10 kHz, then the fixed
       10 kHz TIM3 signal time base */
    Capture_HW_Init(10000);
    Signal_Timer_Init();

    /* Enable the High-Speed device (480 MHz PLL must be ready inside) */
    USBHS_Device_Init(ENABLE);
    printf("USBHS device enabled, real-time stream on EP3 IN\n");

    /* Start the software UART message generator */
    Signal_Start();

    while(1)
    {
        uint16_t blen = 0;
        const uint8_t *blk = Capture_TakeBlock(&blen);
        if(blk != 0 && blen > 0)
        {
            USBHS_SendStream(blk, blen);
            Capture_ReleaseBlock();
        }
        Capture_Diag_Report();
    }
}
