/********************************** (C) COPYRIGHT *******************************
 * File Name          : usb_desc_hs.c
 * Author             : WCH
 * Version            : V1.0.0
 * Date               : 2025/05/26
 * Description        : USB High-Speed device descriptor set. The device keeps
 *                      the same VID/PID (1A86:FE0C) and the same endpoint
 *                      topology as the Full-Speed firmware: EP1 IN interrupt
 *                      notification, EP2 OUT bulk (commands), EP3 IN bulk
 *                      (data). Bulk endpoints use 512-byte packets in the
 *                      High-Speed configuration and 64-byte packets in the
 *                      Full-Speed configuration.
 *********************************************************************************
 * Copyright (c) 2025 Nanjing Qinheng Microelectronics Co., Ltd.
 * Attention: This software (modified or not) and binary are used for
 * microcontroller manufactured by Nanjing Qinheng Microelectronics.
 *******************************************************************************/

#include "usb_desc_hs.h"

/* Device Descriptor (bcdUSB 2.00, High-Speed capable) */
const uint8_t  MyDevDescr[ ] =
{
    0x12,       // bLength
    0x01,       // bDescriptorType (Device)
    0x00, 0x02, // bcdUSB 2.00
    0x02,       // bDeviceClass
    0x00,       // bDeviceSubClass
    0x00,       // bDeviceProtocol
    DEF_USBD_UEP0_SIZE,   // bMaxPacketSize0 64
    (uint8_t)DEF_USB_VID, (uint8_t)(DEF_USB_VID >> 8),  // idVendor  0x1A86
    (uint8_t)DEF_USB_PID, (uint8_t)(DEF_USB_PID >> 8),  // idProduct 0xFE0C
    DEF_IC_PRG_VER, 0x00, // bcdDevice 0.01
    0x01,       // iManufacturer (String Index)
    0x02,       // iProduct (String Index)
    0x03,       // iSerialNumber (String Index)
    0x01,       // bNumConfigurations 1
};

/* Configuration Descriptor (FS): endpoint topology identical to the current
   Full-Speed firmware, so host code sees the same EP1/EP2/EP3 layout. */
const uint8_t  MyCfgDescr_FS[ ] =
{
    /* Configure descriptor */
    0x09, 0x02, 0x43, 0x00, 0x02, 0x01, 0x00, 0x80, 0x32,

    /* Interface 0 (CDC) descriptor */
    0x09, 0x04, 0x00, 0x00, 0x01, 0x02, 0x02, 0x01,  0x00,

    /* Functional Descriptors */
    0x05, 0x24, 0x00, 0x10, 0x01,

    /* Length/management descriptor (data class interface 1) */
    0x05, 0x24, 0x01, 0x00, 0x01,
    0x04, 0x24, 0x02, 0x02,
    0x05, 0x24, 0x06, 0x00, 0x01,

    /* Interrupt upload endpoint descriptor (EP1 IN, 64 bytes) */
    0x07, 0x05, 0x81, 0x03, (uint8_t)DEF_USB_EP1_FS_SIZE, (uint8_t)( DEF_USB_EP1_FS_SIZE >> 8 ), 0x01,

    /* Interface 1 (data interface) descriptor */
    0x09, 0x04, 0x01, 0x00, 0x02, 0x0a, 0x00, 0x00, 0x00,

    /* Endpoint descriptor (EP2 OUT bulk, commands) */
    0x07, 0x05, 0x02, 0x02, (uint8_t)DEF_USB_EP2_FS_SIZE, (uint8_t)( DEF_USB_EP2_FS_SIZE >> 8 ), 0x00,

    /* Endpoint descriptor (EP3 IN bulk, data) */
    0x07, 0x05, 0x83, 0x02, (uint8_t)DEF_USB_EP3_FS_SIZE, (uint8_t)( DEF_USB_EP3_FS_SIZE >> 8 ), 0x00,
};

/* Configuration Descriptor (HS): same topology, bulk endpoints at 512 bytes */
const uint8_t  MyCfgDescr_HS[ ] =
{
    /* Configure descriptor */
    0x09, 0x02, 0x43, 0x00, 0x02, 0x01, 0x00, 0x80, 0x32,

    /* Interface 0 (CDC) descriptor */
    0x09, 0x04, 0x00, 0x00, 0x01, 0x02, 0x02, 0x01, 0x00,

    /* Functional Descriptors */
    0x05, 0x24, 0x00, 0x10, 0x01,

    /* Length/management descriptor (data class interface 1) */
    0x05, 0x24, 0x01, 0x00, 0x01,
    0x04, 0x24, 0x02, 0x02,
    0x05, 0x24, 0x06, 0x00, 0x01,

    /* Interrupt upload endpoint descriptor (EP1 IN, 64 bytes) */
    0x07, 0x05, 0x81, 0x03, (uint8_t)DEF_USB_EP1_FS_SIZE, (uint8_t)( DEF_USB_EP1_FS_SIZE >> 8 ), 0x01,

    /* Interface 1 (data interface) descriptor */
    0x09, 0x04, 0x01, 0x00, 0x02, 0x0a, 0x00, 0x00, 0x00,

    /* Endpoint descriptor (EP2 OUT bulk, commands, 512 bytes) */
    0x07, 0x05, 0x02, 0x02, (uint8_t)DEF_USB_EP2_HS_SIZE, (uint8_t)( DEF_USB_EP2_HS_SIZE >> 8 ), 0x00,

    /* Endpoint descriptor (EP3 IN bulk, data, 512 bytes) */
    0x07, 0x05, 0x83, 0x02, (uint8_t)DEF_USB_EP3_HS_SIZE, (uint8_t)( DEF_USB_EP3_HS_SIZE >> 8 ), 0x00,
};

/* Language Descriptor */
const uint8_t  MyLangDescr[ ] =
{
    0x04, 0x03, 0x09, 0x04
};

/* Manufacturer Descriptor */
const uint8_t  MyManuInfo[ ] =
{
    0x0E,
    0x03,
    'w', 0,
    'c', 0,
    'h', 0,
    '.', 0,
    'c', 0,
    'n', 0
};

/* Product Information */
const uint8_t MyProdInfo[ ]  =
{
    0x12,
    0x03,
    'C', 0,
    'H', 0,
    '3', 0,
    '2', 0,
    'H', 0,
    '4', 0,
    '1', 0,
    '7', 0
};

/* Serial Number Information */
const uint8_t  MySerNumInfo[ ] =
{
    0x16,
    0x03,
    '0', 0,
    '1', 0,
    '2', 0,
    '3', 0,
    '4', 0,
    '5', 0,
    '6', 0,
    '7', 0,
    '8', 0,
    '9', 0
};

/* Device Qualified Descriptor: the device works at High-Speed and can also
   run its other-speed (Full-Speed) configuration. */
const uint8_t MyQuaDesc[ ] =
{
    0x0A, 0x06, 0x00, 0x02, 0xFF, 0xFF, 0xFF, 0x40, 0x01, 0x00,
};

/* Device BOS Descriptor: USB 2.0 extension descriptor, LPM capable */
const uint8_t MyBOSDesc[ ] =
{
    0x05, 0x0F, 0x0C, 0x00, 0x01,
    0x07, 0x10, 0x02, 0x02, 0x00, 0x00, 0x00,
};

/* USB Full-Speed Mode, Other speed configuration Descriptor */
uint8_t TAB_USB_FS_OSC_DESC[ sizeof(MyCfgDescr_HS) ] =
{
    /* Other parts are copied through the program */
    0x09, 0x07,
};

/* USB High-Speed Mode, Other speed configuration Descriptor */
uint8_t TAB_USB_HS_OSC_DESC[ sizeof(MyCfgDescr_FS) ] =
{
    /* Other parts are copied through the program */
    0x09, 0x07,
};
