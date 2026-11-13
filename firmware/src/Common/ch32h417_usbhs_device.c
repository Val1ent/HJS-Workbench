/********************************** (C) COPYRIGHT *******************************
 * File Name          : ch32h417_usbhs_device.c
 * Author             : WCH
 * Version            : V1.0.0
 * Date               : 2025/05/26
 * Description        : This file provides all the USBHS firmware functions for
 *                      the High-Speed controller on PB8/PB9 (USBHSD register
 *                      block, independent from the Full-Speed USBFSD).
 *
 *                      Stage 16C real-time capture stream:
 *                      - CDC enumeration with dual speed config descriptors,
 *                        device qualifier and BOS descriptor (VID/PID 1A86:FE0C).
 *                      - EP1 IN interrupt notification (NAK, not used yet).
 *                      - EP2 OUT bulk receives command bytes and feeds them
 *                        into the shared Signal_HandleRx command parser.
 *                      - EP3 IN bulk streams capture blocks through
 *                        USBHS_SendStream, packed as 512-byte HS packets
 *                        (1000 bytes = 512 + 488). The 16A self-test pattern
 *                        task is retained but no longer called.
 *********************************************************************************
 * Copyright (c) 2025 Nanjing Qinheng Microelectronics Co., Ltd.
 * Attention: This software (modified or not) and binary are used for
 * microcontroller manufactured by Nanjing Qinheng Microelectronics.
 *******************************************************************************/
#include "ch32h417_usbhs_device.h"
#include "ch32h417_usb.h"
#include "hardware.h"

/******************************************************************************/
/* Variable Definition */
/* Global */
const uint8_t *pUSBHS_Descr;

/* Setup Request */
volatile uint8_t  USBHS_SetupReqCode;
volatile uint8_t  USBHS_SetupReqType;
volatile uint16_t USBHS_SetupReqValue;
volatile uint16_t USBHS_SetupReqIndex;
volatile uint16_t USBHS_SetupReqLen;

/* USB Device Status */
volatile uint8_t  USBHS_DevConfig;
volatile uint8_t  USBHS_DevAddr;
volatile uint8_t  USBHS_DevSpeed;
volatile uint8_t  USBHS_DevSleepStatus;
volatile uint8_t  USBHS_DevEnumStatus;
volatile uint16_t USBHS_DevMaxPackLen;

/* CDC line coding from the host: 4 bytes baud (LE), 1 stop bits,
   1 parity, 1 data bits. Default 115200 8N1. */
volatile uint8_t USBHS_LineCoding[7] = {0x00, 0xC2, 0x01, 0x00, 0x00, 0x00, 0x08};

/* EP3 IN data source state. Written by the ISR, read by the main loop. */
volatile uint8_t  USBHS_Ep3_Tx_Done = 0;

/* Endpoint Buffer */
__attribute__ ((aligned(4))) uint8_t USBHS_EP0_Buf[DEF_USBD_UEP0_SIZE];
__attribute__ ((aligned(4))) uint8_t USBHS_EP1_Buf[DEF_USB_EP1_FS_SIZE];
__attribute__ ((aligned(4))) uint8_t USBHS_EP2_Rx_Buf[2 * DEF_USB_EP2_HS_SIZE];
static volatile uint8_t USBHS_Ep2_Rx_Slot = 0;
__attribute__ ((aligned(4))) uint8_t USBHS_EP3_Tx_Buf[DEF_USB_EP3_HS_SIZE];

/******************************************************************************/
/* Interrupt Service Routine Declaration*/
void USBHS_IRQHandler(void) __attribute__((interrupt("WCH-Interrupt-fast")));

/*********************************************************************
 * @fn      USBHS_RCC_Init
 *
 * @brief   Initializes the USB High-Speed clock: independent 480 MHz PLL,
 *          HSE clock source, 25 MHz reference, input divider 1, UTMI enable.
 *
 * @return  none
 */
void USBHS_RCC_Init(FunctionalState sta)
{
    if (sta)
    {
        if((RCC->PLLCFGR & RCC_SYSPLL_SEL) != RCC_SYSPLL_USBHS)
        {
            /* Initialize USBHS 480M PLL */
            RCC_USBHS_PLLCmd(DISABLE);
            RCC_USBHSPLLCLKConfig(RCC_USBHSPLLSource_HSE);
            RCC_USBHSPLLReferConfig(RCC_USBHSPLLRefer_25M);
            RCC_USBHSPLLClockSourceDivConfig(RCC_USBHSPLL_IN_Div1);
            RCC_USBHS_PLLCmd(ENABLE);
            /* The device must not be enabled before the PLL is ready */
            while (!(RCC->CTLR & RCC_USBHS_PLLRDY));
        }
        /* Enable UTMI Clock */
        RCC_UTMIcmd(ENABLE);
        /* Enable USBHS Clock */
        RCC_HBPeriphClockCmd(RCC_HBPeriph_USBHS, ENABLE);
    }
    else
    {
        RCC_HBPeriphClockCmd(RCC_HBPeriph_USBHS, DISABLE);
        RCC_UTMIcmd(DISABLE);
        if((RCC->PLLCFGR & RCC_SYSPLL_SEL) != RCC_SYSPLL_USBHS)
        {
            RCC_USBHS_PLLCmd(DISABLE);
        }
    }
}

/*********************************************************************
 * @fn      USBHS_Device_Endp_Init
 *
 * @brief   Initializes USB device endpoints.
 *
 * @return  none
 */
void USBHS_Device_Endp_Init(void)
{
    USBHSD->UEP_TX_EN = USBHS_UEP0_T_EN | USBHS_UEP1_T_EN | USBHS_UEP3_T_EN;
    USBHSD->UEP_RX_EN = USBHS_UEP0_R_EN | USBHS_UEP2_R_EN;

    USBHSD->UEP0_MAX_LEN = DEF_USBD_UEP0_SIZE;
    USBHSD->UEP1_MAX_LEN = DEF_USB_EP1_FS_SIZE;
    USBHSD->UEP2_MAX_LEN = DEF_USB_EP2_HS_SIZE;
    USBHSD->UEP3_MAX_LEN = DEF_USB_EP3_HS_SIZE;

    USBHSD->UEP0_DMA = (uint32_t)(uint8_t *)USBHS_EP0_Buf;
    USBHSD->UEP1_TX_DMA = (uint32_t)(uint8_t *)USBHS_EP1_Buf;
    USBHS_Ep2_Rx_Slot = 0;
    USBHSD->UEP2_RX_DMA = (uint32_t)(uint8_t *)&USBHS_EP2_Rx_Buf[0];
    USBHSD->UEP3_TX_DMA = (uint32_t)(uint8_t *)USBHS_EP3_Tx_Buf;

    USBHSD->UEP0_TX_LEN = 0;
    USBHSD->UEP0_TX_CTRL = USBHS_UEP_T_RES_NAK;
    USBHSD->UEP0_RX_CTRL = USBHS_UEP_R_RES_ACK;

    USBHSD->UEP1_TX_LEN = 0;
    USBHSD->UEP1_TX_CTRL = USBHS_UEP_T_RES_NAK;

    USBHSD->UEP2_RX_CTRL = USBHS_UEP_R_RES_ACK;

    USBHSD->UEP3_TX_LEN = 0;
    USBHSD->UEP3_TX_CTRL = USBHS_UEP_T_RES_NAK;
}

/*********************************************************************
 * @fn      USBHS_Device_Init
 *
 * @brief   Initializes USB High-Speed device.
 *
 * @return  none
 */
void USBHS_Device_Init(FunctionalState sta)
{
    if(sta)
    {
        USBHS_RCC_Init(ENABLE);
        USBHSD->CONTROL = USBHS_UD_RST_LINK | USBHS_UD_PHY_SUSPENDM;
        USBHSD->INT_EN = USBHS_UDIE_BUS_RST | USBHS_UDIE_SUSPEND | USBHS_UDIE_BUS_SLEEP | USBHS_UDIE_LPM_ACT | USBHS_UDIE_TRANSFER | USBHS_UDIE_LINK_RDY;
        USBHS_Device_Endp_Init();
        USBHSD->BASE_MODE = USBHS_UD_SPEED_HIGH;
        USBHSD->CONTROL = USBHS_UD_DEV_EN | USBHS_UD_DMA_EN | USBHS_UD_LPM_EN | USBHS_UD_PHY_SUSPENDM;
        NVIC_EnableIRQ(USBHS_IRQn);

        /* Prime the first EP3 IN stream packet (done flag starts asserted) */
        USBHS_Ep3_Tx_Done = 1;
    }
    else
    {
        USBHSD->CONTROL = USBHS_UD_RST_SIE | USBHS_UD_RST_LINK;
        NVIC_DisableIRQ(USBHS_IRQn);
        USBHS_RCC_Init(DISABLE);
    }
}

/*********************************************************************
 * @fn      USBHS_SendStream
 *
 * @brief   Streams an arbitrary byte range over EP3 IN in packets of at
 *          most 512 bytes (a 1000-byte capture block ships as 512 + 488;
 *          the trailing 488-byte packet is a legal HS short packet).
 *
 *          Each packet waits for the previous one to be confirmed by the
 *          ISR (USBHS_Ep3_Tx_Done), then reloads the shared EP3 buffer and
 *          arms the endpoint. The DATA toggle is owned by the ISR and is
 *          never touched here, otherwise the packet PID sequence breaks.
 *          No packet is queued for a zero length.
 *
 * @param   data - bytes to stream
 * @param   len  - number of bytes to stream
 *
 * @return  none
 */
void USBHS_SendStream(const uint8_t *data, uint16_t len)
{
    uint16_t off = 0;
    while(off < len)
    {
        uint16_t chunk = len - off;
        if(chunk > DEF_USB_EP3_HS_SIZE) chunk = DEF_USB_EP3_HS_SIZE;
        while(!USBHS_Ep3_Tx_Done)
        {
            /* previous packet still in flight, keep waiting */
        }
        USBHS_Ep3_Tx_Done = 0;
        memcpy(USBHS_EP3_Tx_Buf, data + off, chunk);
        USBHSD->UEP3_TX_LEN = chunk;
        USBHSD->UEP3_TX_CTRL = (USBHSD->UEP3_TX_CTRL & ~USBHS_UEP_T_RES_MASK) | USBHS_UEP_T_RES_ACK;
        off += chunk;
    }
}

/*********************************************************************
 * @fn      USBHS_IRQHandler
 *
 * @brief   This function handles USBHS exception.
 *
 * @return  none
 */
void USBHS_IRQHandler(void)
{
    uint8_t intflag, intst, errflag;
    uint16_t len;
    uint8_t endp_num;

    intflag = USBHSD->INT_FG;
    intst = USBHSD->INT_ST;

    if(intflag & USBHS_UDIF_TRANSFER)
    {
        endp_num = intst & USBHS_UDIS_EP_ID_MASK;
        if(!(intst & USBHS_UDIS_EP_DIR))  // SETUP/OUT Transaction
        {
            switch(endp_num)
            {
            case DEF_UEP0:
                USBHSD->UEP0_RX_CTRL &= ~USBHS_UEP_R_DONE;
                if(USBHSD->UEP0_RX_CTRL & USBHS_UEP_R_SETUP_IS)
                {
                    /* Store All Setup Values */
                    USBHS_SetupReqType = pUSBHS_SetupReqPak->bRequestType;
                    USBHS_SetupReqCode = pUSBHS_SetupReqPak->bRequest;
                    USBHS_SetupReqLen = pUSBHS_SetupReqPak->wLength;
                    USBHS_SetupReqValue = pUSBHS_SetupReqPak->wValue;
                    USBHS_SetupReqIndex = pUSBHS_SetupReqPak->wIndex;

                    len = 0;
                    errflag = 0;
                    if((USBHS_SetupReqType & USB_REQ_TYP_MASK) != USB_REQ_TYP_STANDARD)
                    {
                        /* usb non-standard request processing */
                        if(USBHS_SetupReqType & USB_REQ_TYP_CLASS)
                        {
                            /* Class requests */
                            switch(USBHS_SetupReqCode)
                            {
                            case CDC_GET_LINE_CODING:
                                len = 7;
                                memcpy(USBHS_EP0_Buf, (uint8_t *)&USBHS_LineCoding[0], len);
                                break;

                            case CDC_SET_LINE_CODING:
                                break;

                            case CDC_SET_LINE_CTLSTE:
                                break;

                            case CDC_SEND_BREAK:
                                break;

                            default:
                                errflag = 0xff;
                                break;
                            }
                        }
                        else if(USBHS_SetupReqType & USB_REQ_TYP_VENDOR)
                        {
                            /* Manufacturer request */
                            errflag = 0xFF;
                        }
                        else
                        {
                            errflag = 0xFF;
                        }
                    }
                    else
                    {
                        /* usb standard request processing */
                        switch(USBHS_SetupReqCode)
                        {
                        /* get device/configuration/string/report/... descriptors */
                        case USB_GET_DESCRIPTOR:
                            switch((uint8_t)(USBHS_SetupReqValue >> 8))
                            {
                            /* get usb device descriptor */
                            case USB_DESCR_TYP_DEVICE:
                                pUSBHS_Descr = MyDevDescr;
                                len = DEF_USBD_DEVICE_DESC_LEN;
                                break;

                            /* get usb configuration descriptor */
                            case USB_DESCR_TYP_CONFIG:
                                /* Query current usb speed */
                                if(USBHSD->MIS_ST & USBHS_UDMS_HS_MOD)
                                {
                                    /* High speed mode */
                                    USBHS_DevSpeed = USBHS_SPEED_HIGH;
                                    USBHS_DevMaxPackLen = DEF_USBD_HS_PACK_SIZE;
                                }
                                else
                                {
                                    /* Full speed mode */
                                    USBHS_DevSpeed = USBHS_SPEED_FULL;
                                    USBHS_DevMaxPackLen = DEF_USBD_FS_PACK_SIZE;
                                }

                                /* Load usb configuration descriptor by speed */
                                if(USBHS_DevSpeed == USBHS_SPEED_HIGH)
                                {
                                    /* High speed mode */
                                    pUSBHS_Descr = MyCfgDescr_HS;
                                    len = DEF_USBD_CONFIG_HS_DESC_LEN;
                                }
                                else
                                {
                                    /* Full speed mode */
                                    pUSBHS_Descr = MyCfgDescr_FS;
                                    len = DEF_USBD_CONFIG_FS_DESC_LEN;
                                }
                                break;

                            /* get usb string descriptor */
                            case USB_DESCR_TYP_STRING:
                                switch((uint8_t)(USBHS_SetupReqValue & 0xFF))
                                {
                                /* Descriptor 0, Language descriptor */
                                case DEF_STRING_DESC_LANG:
                                    pUSBHS_Descr = MyLangDescr;
                                    len = DEF_USBD_LANG_DESC_LEN;
                                    break;

                                /* Descriptor 1, Manufacturers String descriptor */
                                case DEF_STRING_DESC_MANU:
                                    pUSBHS_Descr = MyManuInfo;
                                    len = DEF_USBD_MANU_DESC_LEN;
                                    break;

                                /* Descriptor 2, Product String descriptor */
                                case DEF_STRING_DESC_PROD:
                                    pUSBHS_Descr = MyProdInfo;
                                    len = DEF_USBD_PROD_DESC_LEN;
                                    break;

                                /* Descriptor 3, Serial-number String descriptor */
                                case DEF_STRING_DESC_SERN:
                                    pUSBHS_Descr = MySerNumInfo;
                                    len = DEF_USBD_SN_DESC_LEN;
                                    break;

                                default:
                                    errflag = 0xFF;
                                    break;
                                }
                                break;

                            /* get usb device qualify descriptor */
                            case USB_DESCR_TYP_QUALIF:
                                pUSBHS_Descr = MyQuaDesc;
                                len = DEF_USBD_QUALFY_DESC_LEN;
                                break;

                            /* get usb BOS descriptor */
                            case USB_DESCR_TYP_BOS:
                                pUSBHS_Descr = MyBOSDesc;
                                len = DEF_USBD_BOS_DESC_LEN;
                                break;

                            /* get usb other-speed descriptor */
                            case USB_DESCR_TYP_SPEED:
                                if(USBHS_DevSpeed == USBHS_SPEED_HIGH)
                                {
                                    /* High speed mode */
                                    memcpy(&TAB_USB_HS_OSC_DESC[2], &MyCfgDescr_FS[2], DEF_USBD_CONFIG_FS_DESC_LEN - 2);
                                    pUSBHS_Descr = (uint8_t *)&TAB_USB_HS_OSC_DESC[0];
                                    len = DEF_USBD_CONFIG_FS_DESC_LEN;
                                }
                                else if(USBHS_DevSpeed == USBHS_SPEED_FULL)
                                {
                                    /* Full speed mode */
                                    memcpy(&TAB_USB_FS_OSC_DESC[2], &MyCfgDescr_HS[2], DEF_USBD_CONFIG_HS_DESC_LEN - 2);
                                    pUSBHS_Descr = (uint8_t *)&TAB_USB_FS_OSC_DESC[0];
                                    len = DEF_USBD_CONFIG_HS_DESC_LEN;
                                }
                                else
                                {
                                    errflag = 0xFF;
                                }
                                break;

                            default:
                                errflag = 0xFF;
                                break;
                            }

                            /* Copy Descriptors to Endp0 DMA buffer */
                            if(USBHS_SetupReqLen > len)
                            {
                                USBHS_SetupReqLen = len;
                            }
                            len = (USBHS_SetupReqLen >= DEF_USBD_UEP0_SIZE) ? DEF_USBD_UEP0_SIZE : USBHS_SetupReqLen;
                            memcpy(USBHS_EP0_Buf, pUSBHS_Descr, len);
                            pUSBHS_Descr += len;
                            break;

                        /* Set usb address */
                        case USB_SET_ADDRESS:
                            USBHS_DevAddr = (uint8_t)(USBHS_SetupReqValue & 0xFF);
                            break;

                        /* Get usb configuration now set */
                        case USB_GET_CONFIGURATION:
                            USBHS_EP0_Buf[0] = USBHS_DevConfig;
                            if(USBHS_SetupReqLen > 1)
                            {
                                USBHS_SetupReqLen = 1;
                            }
                            break;

                        /* Set usb configuration to use */
                        case USB_SET_CONFIGURATION:
                            USBHS_DevConfig = (uint8_t)(USBHS_SetupReqValue & 0xFF);
                            USBHS_DevEnumStatus = 0x01;
                            break;

                        /* Clear or disable one usb feature */
                        case USB_CLEAR_FEATURE:
                            if((USBHS_SetupReqType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_DEVICE)
                            {
                                /* clear one device feature */
                                if((uint8_t)(USBHS_SetupReqValue & 0xFF) == USB_REQ_FEAT_REMOTE_WAKEUP)
                                {
                                    /* clear usb sleep status, device not prepare to sleep */
                                    USBHS_DevSleepStatus &= ~0x01;
                                }
                                else
                                {
                                    errflag = 0xFF;
                                }
                            }
                            else if((USBHS_SetupReqType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_ENDP)
                            {
                                /* Clear End-point Feature */
                                if((uint8_t)(USBHS_SetupReqValue & 0xFF) == USB_REQ_FEAT_ENDP_HALT)
                                {
                                    switch((uint8_t)(USBHS_SetupReqIndex & 0xFF))
                                    {
                                    case(DEF_UEP1 | DEF_UEP_IN):
                                        /* Set End-point 1 IN NAK */
                                        USBHSD->UEP1_TX_CTRL = USBHS_UEP_T_RES_NAK;
                                        break;

                                    case(DEF_UEP2 | DEF_UEP_OUT):
                                        /* Set End-point 2 OUT ACK */
                                        USBHSD->UEP2_RX_CTRL = USBHS_UEP_R_RES_ACK;
                                        break;

                                    case(DEF_UEP3 | DEF_UEP_IN):
                                        /* Set End-point 3 IN NAK */
                                        USBHSD->UEP3_TX_CTRL = USBHS_UEP_T_RES_NAK;
                                        break;

                                    default:
                                        errflag = 0xFF;
                                        break;
                                    }
                                }
                                else
                                {
                                    errflag = 0xFF;
                                }
                            }
                            else
                            {
                                errflag = 0xFF;
                            }
                            break;

                        /* set or enable one usb feature */
                        case USB_SET_FEATURE:
                            if((USBHS_SetupReqType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_DEVICE)
                            {
                                /* Set Device Feature */
                                if((uint8_t)(USBHS_SetupReqValue & 0xFF) == USB_REQ_FEAT_REMOTE_WAKEUP)
                                {
                                    if(((USBHS_DevSpeed == USBHS_SPEED_HIGH) && (MyCfgDescr_HS[7] & 0x20)) ||
                                       ((USBHS_DevSpeed == USBHS_SPEED_FULL) && (MyCfgDescr_FS[7] & 0x20)))
                                    {
                                        /* Set Wake-up flag, device prepare to sleep */
                                        USBHS_DevSleepStatus |= 0x01;
                                    }
                                    else
                                    {
                                        errflag = 0xFF;
                                    }
                                }
                                else
                                {
                                    errflag = 0xFF;
                                }
                            }
                            else if((USBHS_SetupReqType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_ENDP)
                            {
                                /* Set End-point Feature */
                                if((uint8_t)(USBHS_SetupReqValue & 0xFF) == USB_REQ_FEAT_ENDP_HALT)
                                {
                                    /* Set end-points status stall */
                                    switch((uint8_t)(USBHS_SetupReqIndex & 0xFF))
                                    {
                                    case(DEF_UEP1 | DEF_UEP_IN):
                                        /* Set End-point 1 IN STALL */
                                        USBHSD->UEP1_TX_CTRL = (USBHSD->UEP1_TX_CTRL & ~USBHS_UEP_T_RES_MASK) | USBHS_UEP_T_RES_STALL;
                                        break;

                                    case(DEF_UEP2 | DEF_UEP_OUT):
                                        /* Set End-point 2 OUT STALL */
                                        USBHSD->UEP2_RX_CTRL = (USBHSD->UEP2_RX_CTRL & ~USBHS_UEP_R_RES_MASK) | USBHS_UEP_R_RES_STALL;
                                        break;

                                    case(DEF_UEP3 | DEF_UEP_IN):
                                        /* Set End-point 3 IN STALL */
                                        USBHSD->UEP3_TX_CTRL = (USBHSD->UEP3_TX_CTRL & ~USBHS_UEP_T_RES_MASK) | USBHS_UEP_T_RES_STALL;
                                        break;

                                    default:
                                        errflag = 0xFF;
                                        break;
                                    }
                                }
                                else
                                {
                                    errflag = 0xFF;
                                }
                            }
                            else
                            {
                                errflag = 0xFF;
                            }
                            break;

                        /* This request allows the host to select another setting for the specified interface  */
                        case USB_GET_INTERFACE:
                            USBHS_EP0_Buf[0] = 0x00;
                            if(USBHS_SetupReqLen > 1)
                            {
                                USBHS_SetupReqLen = 1;
                            }
                            break;

                        case USB_SET_INTERFACE:
                            break;

                        /* host get status of specified device/interface/end-points */
                        case USB_GET_STATUS:
                            USBHS_EP0_Buf[0] = 0x00;
                            USBHS_EP0_Buf[1] = 0x00;
                            if((USBHS_SetupReqType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_ENDP)
                            {
                                switch((uint8_t)(USBHS_SetupReqIndex & 0xFF))
                                {
                                case(DEF_UEP1 | DEF_UEP_IN):
                                    if(((USBHSD->UEP1_TX_CTRL) & USBHS_UEP_T_RES_MASK) == USBHS_UEP_T_RES_STALL)
                                    {
                                        USBHS_EP0_Buf[0] = 0x01;
                                    }
                                    break;

                                case(DEF_UEP2 | DEF_UEP_OUT):
                                    if(((USBHSD->UEP2_RX_CTRL) & USBHS_UEP_R_RES_MASK) == USBHS_UEP_R_RES_STALL)
                                    {
                                        USBHS_EP0_Buf[0] = 0x01;
                                    }
                                    break;

                                case(DEF_UEP3 | DEF_UEP_IN):
                                    if(((USBHSD->UEP3_TX_CTRL) & USBHS_UEP_T_RES_MASK) == USBHS_UEP_T_RES_STALL)
                                    {
                                        USBHS_EP0_Buf[0] = 0x01;
                                    }
                                    break;

                                default:
                                    errflag = 0xFF;
                                    break;
                                }
                            }
                            else if((USBHS_SetupReqType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_DEVICE)
                            {
                                if(USBHS_DevSleepStatus & 0x01)
                                {
                                    USBHS_EP0_Buf[0] = 0x02;
                                }
                            }
                            else
                            {
                                errflag = 0xFF;
                            }

                            if(USBHS_SetupReqLen > 2)
                            {
                                USBHS_SetupReqLen = 2;
                            }
                            break;

                        default:
                            errflag = 0xFF;
                            break;
                        }
                    }

                    /* errflag = 0xFF means a request not support or some errors occurred, else correct */
                    if(errflag == 0xFF)
                    {
                        /* if one request not support, return stall */
                        USBHSD->UEP0_TX_CTRL = USBHS_UEP_T_TOG_DATA1 | USBHS_UEP_T_RES_STALL;
                        USBHSD->UEP0_RX_CTRL = USBHS_UEP_R_TOG_DATA1 | USBHS_UEP_R_RES_STALL;
                    }
                    else
                    {
                        /* end-point 0 data Tx/Rx */
                        if(USBHS_SetupReqType & DEF_UEP_IN)
                        {
                            /* tx */
                            len = (USBHS_SetupReqLen > DEF_USBD_UEP0_SIZE) ? DEF_USBD_UEP0_SIZE : USBHS_SetupReqLen;
                            USBHS_SetupReqLen -= len;
                            USBHSD->UEP0_TX_LEN = len;
                            USBHSD->UEP0_TX_CTRL = USBHS_UEP_T_TOG_DATA1 | USBHS_UEP_T_RES_ACK;
                        }
                        else
                        {
                            /* rx */
                            if(USBHS_SetupReqLen == 0)
                            {
                                USBHSD->UEP0_TX_LEN = 0;
                                USBHSD->UEP0_TX_CTRL = USBHS_UEP_T_TOG_DATA1 | USBHS_UEP_T_RES_ACK;
                            }
                            else
                            {
                                USBHSD->UEP0_RX_CTRL = USBHS_UEP_R_TOG_DATA1 | USBHS_UEP_R_RES_ACK;
                            }
                        }
                    }
                }
                /* end-point 0 data out interrupt */
                else
                {
                    USBHSD->UEP0_RX_CTRL = USBHS_UEP_R_RES_NAK;  // clear
                    len = USBHSD->UEP0_RX_LEN;

                    /* if any processing about rx, set it here */
                    if((USBHS_SetupReqType & USB_REQ_TYP_MASK) != USB_REQ_TYP_STANDARD)
                    {
                        USBHS_SetupReqLen = 0;
                        /* Non-standard request end-point 0 Data download */
                        if(USBHS_SetupReqCode == CDC_SET_LINE_CODING)
                        {
                            /* Save relevant parameters such as serial port baud rate.
                               The 7 downlinked bytes are, in order:
                               4 bytes baud rate (LSB first), 1 byte stop bits,
                               1 byte parity, 1 byte data bits. */
                            USBHS_LineCoding[0] = USBHS_EP0_Buf[0];
                            USBHS_LineCoding[1] = USBHS_EP0_Buf[1];
                            USBHS_LineCoding[2] = USBHS_EP0_Buf[2];
                            USBHS_LineCoding[3] = USBHS_EP0_Buf[3];
                            USBHS_LineCoding[4] = USBHS_EP0_Buf[4];
                            USBHS_LineCoding[5] = USBHS_EP0_Buf[5];
                            USBHS_LineCoding[6] = USBHS_EP0_Buf[6];
                        }
                    }
                    else
                    {
                        /* Standard request end-point 0 Data download */
                    }

                    if(USBHS_SetupReqLen == 0)
                    {
                        USBHSD->UEP0_TX_LEN = 0;
                        USBHSD->UEP0_TX_CTRL = USBHS_UEP_T_TOG_DATA1 | USBHS_UEP_T_RES_ACK;
                    }
                }
                break;

            /* end-point 2 data out interrupt: parse the received bytes from
               the current ping-pong slot, re-arm the RX DMA on the other
               slot, then re-write RX_CTRL so the endpoint keeps ACKing.
               Empty packets fall through Signal_HandleRx unchanged. */
            case DEF_UEP2:
            {
                uint8_t cur_slot = USBHS_Ep2_Rx_Slot;
                USBHSD->UEP2_RX_CTRL &= ~USBHS_UEP_R_DONE;
                USBHSD->UEP2_RX_CTRL ^= USBHS_UEP_R_TOG_DATA1;
                Signal_HandleRx(&USBHS_EP2_Rx_Buf[cur_slot * DEF_USB_EP2_HS_SIZE],
                                USBHSD->UEP2_RX_LEN);
                USBHS_Ep2_Rx_Slot = (uint8_t)(cur_slot ^ 1);
                USBHSD->UEP2_RX_DMA =
                    (uint32_t)(uint8_t *)&USBHS_EP2_Rx_Buf[USBHS_Ep2_Rx_Slot * DEF_USB_EP2_HS_SIZE];
                /* Re-write the response bits after moving RX_DMA. On the USBHS
                   controller the endpoint only re-enters receive-ready when the
                   software writes RX_CTRL; reprogramming RX_DMA alone leaves it
                   stopped after the first packet. Keep it ACKing. */
                USBHSD->UEP2_RX_CTRL &= ~USBHS_UEP_R_RES_MASK;
                USBHSD->UEP2_RX_CTRL |= USBHS_UEP_R_RES_ACK;
                break;
            }

            default:
                break;
            }
        }
        else
        {
            /* data-in stage processing */
            switch(endp_num)
            {
            /* end-point 0 data in interrupt */
            case DEF_UEP0:
                USBHSD->UEP0_TX_CTRL &= ~USBHS_UEP_T_DONE;
                if(USBHS_SetupReqLen == 0)
                {
                    USBHSD->UEP0_RX_CTRL = USBHS_UEP_R_TOG_DATA1 | USBHS_UEP_R_RES_ACK;
                }
                if((USBHS_SetupReqType & USB_REQ_TYP_MASK) != USB_REQ_TYP_STANDARD)
                {
                    /* Non-standard request endpoint 0 Data upload */
                }
                else
                {
                    /* Standard request endpoint 0 Data upload */
                    switch(USBHS_SetupReqCode)
                    {
                    case USB_GET_DESCRIPTOR:
                        len = USBHS_SetupReqLen >= DEF_USBD_UEP0_SIZE ? DEF_USBD_UEP0_SIZE : USBHS_SetupReqLen;
                        memcpy(USBHS_EP0_Buf, pUSBHS_Descr, len);
                        USBHS_SetupReqLen -= len;
                        pUSBHS_Descr += len;
                        USBHSD->UEP0_TX_LEN = len;
                        USBHSD->UEP0_TX_CTRL ^= USBHS_UEP_T_TOG_DATA1;
                        USBHSD->UEP0_TX_CTRL = (USBHSD->UEP0_TX_CTRL & ~USBHS_UEP_T_RES_MASK) | USBHS_UEP_T_RES_ACK;
                        break;

                    case USB_SET_ADDRESS:
                        USBHSD->DEV_AD = USBHS_DevAddr;
                        break;

                    default:
                        USBHSD->UEP0_TX_LEN = 0;
                        break;
                    }
                }
                break;

            /* end-point 1 data in interrupt (notification, kept NAK) */
            case DEF_UEP1:
                USBHSD->UEP1_TX_CTRL &= ~USBHS_UEP_T_DONE;
                USBHSD->UEP1_TX_CTRL ^= USBHS_UEP_T_TOG_DATA1;
                USBHSD->UEP1_TX_CTRL = (USBHSD->UEP1_TX_CTRL & ~USBHS_UEP_T_RES_MASK) | USBHS_UEP_T_RES_NAK;
                break;

            /* end-point 3 data in interrupt: packet sent, ask the main loop
               for the next self-test pattern packet */
            case DEF_UEP3:
                USBHSD->UEP3_TX_CTRL &= ~USBHS_UEP_T_DONE;
                USBHSD->UEP3_TX_CTRL ^= USBHS_UEP_T_TOG_DATA1;
                USBHSD->UEP3_TX_CTRL = (USBHSD->UEP3_TX_CTRL & ~USBHS_UEP_T_RES_MASK) | USBHS_UEP_T_RES_NAK;
                USBHS_Ep3_Tx_Done = 1;
                break;

            default:
                break;
            }
        }
    }

    else if(intflag & USBHS_UDIF_LINK_RDY)
    {
        USBHSD->INT_FG = USBHS_UDIF_LINK_RDY;
    }
    else if(intflag & USBHS_UDIF_SUSPEND)
    {
        USBHSD->INT_FG = USBHS_UDIF_SUSPEND;
        /* usb suspend interrupt processing */
        if(USBHSD->MIS_ST & USBHS_UDMS_SUSPEND)
        {
            USBHS_DevSleepStatus |= 0x02;
            if(USBHS_DevSleepStatus == 0x03)
            {
                /* Handling usb sleep here */
            }
        }
        else
        {
            USBHS_DevSleepStatus &= ~0x02;
        }
    }
    else if(intflag & USBHS_UDIF_BUS_RST)
    {
        /* usb reset interrupt processing */
        USBHS_DevConfig = 0;
        USBHS_DevAddr = 0;
        USBHS_DevSleepStatus = 0;
        USBHS_DevEnumStatus = 0;

        USBHSD->DEV_AD = 0;
        USBHS_Device_Endp_Init();

        /* Restore default line coding 115200 8N1 */
        USBHS_LineCoding[0] = 0x00;
        USBHS_LineCoding[1] = 0xC2;
        USBHS_LineCoding[2] = 0x01;
        USBHS_LineCoding[3] = 0x00;
        USBHS_LineCoding[4] = 0x00;
        USBHS_LineCoding[5] = 0x00;
        USBHS_LineCoding[6] = 0x08;

        /* Prime the first EP3 IN stream packet again */
        USBHS_Ep3_Tx_Done = 1;

        USBHSD->INT_FG = USBHS_UDIF_BUS_RST;
    }
    else
    {
        /* other interrupts */
        USBHSD->INT_FG = intflag;
    }
}
