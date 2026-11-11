/********************************** (C) COPYRIGHT *******************************
* File Name          : dma_capture.h
* Author             : WCH
* Version            : V1.0.0
* Date               : 2026/11/10
* Description        : TIM2 update events hardware-trigger DMA1_Channel1 to move
*                      the GPIOD input register byte into RAM without CPU
*                      involvement. The module boots in single-buffer mode,
*                      then promotes itself to double-buffer mode and hands
*                      full 1000-byte blocks to the main loop. TIM3 provides
*                      the fixed 10 kHz time base that drives the signal
*                      generator, independent of the sampling rate.
*********************************************************************************
* Copyright (c) 2025 Nanjing Qinheng Microelectronics Co., Ltd.
* Attention: This software (modified or not) and binary are used for
* microcontroller manufactured by Nanjing Qinheng Microelectronics.
*******************************************************************************/
#ifndef __DMA_CAPTURE_H
#define __DMA_CAPTURE_H

#ifdef __cplusplus
 extern "C" {
#endif

#include "ch32h417.h"

void Capture_HW_Init(uint32_t sample_rate);
int  Capture_SetRate(uint32_t sample_rate);
const uint8_t* Capture_TakeBlock(uint16_t *out_len);
void Capture_ReleaseBlock(void);
uint32_t Capture_OverflowCount(void);
uint32_t Capture_ErrorCount(void);
uint32_t Capture_CurrentRate(void);
uint32_t Capture_RejectCount(void);
void Signal_Timer_Init(void);

#ifdef __cplusplus
}
#endif

#endif
