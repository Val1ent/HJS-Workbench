/********************************** (C) COPYRIGHT *******************************
* File Name          : UART.C
* Author             : WCH
* Version            : V1.01
* Date               : 2024/01/19
* Description        : uart serial port related initialization and processing
*******************************************************************************
* Copyright (c) 2025 Nanjing Qinheng Microelectronics Co., Ltd.
* Attention: This software (modified or not) and binary are used for 
* microcontroller manufactured by Nanjing Qinheng Microelectronics.
*******************************************************************************/

#include "UART.h"
#include "hardware.h"
#include "ch32h417_usb.h"
/*******************************************************************************/
/* Variable Definition */
/* Global */

/* The following are serial port transmit and receive related variables and buffers */
volatile UART_CTL Uart;

/*********************************************************************
 * @fn      RCC_Configuration
 *
 * @brief   Configures the different system clocks.
 *
 * @return  none
 */
uint8_t RCC_Configuration( void )
{
    RCC_HB2PeriphClockCmd( RCC_HB2Periph_AFIO | RCC_HB2Periph_GPIOF | RCC_HB2Periph_GPIOA, ENABLE );
    RCC_HB1PeriphClockCmd( RCC_HB1Periph_USART4 | RCC_HB1Periph_TIM2, ENABLE );
    RCC_HBPeriphClockCmd( RCC_HBPeriph_DMA1, ENABLE );
    return 0;
}

/*********************************************************************
 * @fn      UART_ParaInit
 *
 * @brief   CDC2 parameters initialization
 *          mode = 0 : Used in usb modify initialization
 *          mode = 1 : Used in default initializations
 * @return  none
 */
void UART_ParaInit( uint8_t mode )
{
    uint8_t i;

    Uart.Rx_LoadPtr = 0x00;
    Uart.Rx_DealPtr = 0x00;
    Uart.Rx_RemainLen = 0x00;
    Uart.Rx_TimeOut = 0x00;
    Uart.Rx_TimeOutMax = 30;

    Uart.Tx_LoadNum = 0x00;
    Uart.Tx_DealNum = 0x00;
    Uart.Tx_RemainNum = 0x00;
    for( i = 0; i < DEF_UARTx_TX_BUF_NUM_MAX; i++ )
    {
        Uart.Tx_PackLen[ i ] = 0x00;
    }
    Uart.Tx_Flag = 0x00;
    Uart.Tx_CurPackLen = 0x00;
    Uart.Tx_CurPackPtr = 0x00;

    Uart.USB_Up_IngFlag = 0x00;
    Uart.USB_Up_TimeOut = 0x00;
    Uart.USB_Up_Pack0_Flag = 0x00;
    Uart.USB_Down_StopFlag = 0x00;

    if( mode )
    {
        Uart.Com_Cfg[ 0 ] = (uint8_t)( DEF_UARTx_BAUDRATE );
        Uart.Com_Cfg[ 1 ] = (uint8_t)( DEF_UARTx_BAUDRATE >> 8 );
        Uart.Com_Cfg[ 2 ] = (uint8_t)( DEF_UARTx_BAUDRATE >> 16 );
        Uart.Com_Cfg[ 3 ] = (uint8_t)( DEF_UARTx_BAUDRATE >> 24 );
        Uart.Com_Cfg[ 4 ] = DEF_UARTx_STOPBIT;
        Uart.Com_Cfg[ 5 ] = DEF_UARTx_PARITY;
        Uart.Com_Cfg[ 6 ] = DEF_UARTx_DATABIT;
        Uart.Com_Cfg[ 7 ] = DEF_UARTx_RX_TIMEOUT;
    }
}

