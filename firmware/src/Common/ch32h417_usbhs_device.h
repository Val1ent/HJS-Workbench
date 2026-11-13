/********************************** (C) COPYRIGHT *******************************
 * File Name          : ch32h417_usbhs_device.h
 * Author             : WCH
 * Version            : V1.0.0
 * Date               : 2025/05/26
 * Description        : Header of the USB High-Speed device firmware functions.
 *                      Uses the USBHSD register block on PB8/PB9, independent
 *                      from the Full-Speed USBFSD controller.
 *********************************************************************************
 * Copyright (c) 2025 Nanjing Qinheng Microelectronics Co., Ltd.
 * Attention: This software (modified or not) and binary are used for
 * microcontroller manufactured by Nanjing Qinheng Microelectronics.
 *******************************************************************************/

#ifndef __CH32H417_USBHS_DEVICE_H__
#define __CH32H417_USBHS_DEVICE_H__

/*******************************************************************************/
/* Header File */
#include "ch32h417_conf.h"
#include "string.h"
#include "usb_desc_hs.h"

#ifdef __cplusplus
extern "C" {
#endif

/*******************************************************************************/
/* Macro Definition */

/* General */
#define pUSBHS_SetupReqPak            ((PUSB_SETUP_REQ)USBHS_EP0_Buf)

#define DEF_UEP_IN                    0x80
#define DEF_UEP_OUT                   0x00
/* Endpoint Number */
#define DEF_UEP_BUSY                  0x01
#define DEF_UEP_FREE                  0x00
#define DEF_UEP_NUM                   16
#define DEF_UEP0                      0x00
#define DEF_UEP1                      0x01
#define DEF_UEP2                      0x02
#define DEF_UEP3                      0x03

/* USB SPEED TYPE */
#define USBHS_SPEED_TYPE_MASK         ((uint8_t)(0x03))
#define USBHS_SPEED_LOW               ((uint8_t)(0x02))
#define USBHS_SPEED_FULL              ((uint8_t)(0x00))
#define USBHS_SPEED_HIGH              ((uint8_t)(0x01))

/******************************************************************************/
/* Variable Declaration */

/* SetUp Request Values */
extern const uint8_t *pUSBHS_Descr;

/* Setup Request */
extern volatile uint8_t  USBHS_SetupReqCode;
extern volatile uint8_t  USBHS_SetupReqType;
extern volatile uint16_t USBHS_SetupReqValue;
extern volatile uint16_t USBHS_SetupReqIndex;
extern volatile uint16_t USBHS_SetupReqLen;

/* USB Device Status */
extern volatile uint8_t  USBHS_DevConfig;
extern volatile uint8_t  USBHS_DevAddr;
extern volatile uint8_t  USBHS_DevSleepStatus;
extern volatile uint8_t  USBHS_DevEnumStatus;
extern volatile uint16_t USBHS_DevMaxPackLen;
extern volatile uint8_t  USBHS_DevSpeed;

/* Endpoint Buffer */
extern __attribute__ ((aligned(4))) uint8_t USBHS_EP0_Buf[ DEF_USBD_UEP0_SIZE ];
extern __attribute__ ((aligned(4))) uint8_t USBHS_EP2_Rx_Buf[ 2 * DEF_USB_EP2_HS_SIZE ];
extern __attribute__ ((aligned(4))) uint8_t USBHS_EP3_Tx_Buf[ DEF_USB_EP3_HS_SIZE ];

/* CDC line coding received from the host (SET_LINE_CODING) */
extern volatile uint8_t USBHS_LineCoding[ 7 ];

/* EP3 IN data source state, shared between ISR and main loop (volatile) */
extern volatile uint8_t  USBHS_Ep3_Tx_Done;   /* 1: last packet sent, load next */

/********************************************************************************/
/* Function Declaration */
extern void USBHS_Device_Endp_Init ( void );
extern void USBHS_Device_Init ( FunctionalState sta );
extern void USBHS_RCC_Init ( FunctionalState sta );
extern void USBHS_IRQHandler( void );
extern void USBHS_SendStream( const uint8_t *data, uint16_t len );

#ifdef __cplusplus
}
#endif


#endif
