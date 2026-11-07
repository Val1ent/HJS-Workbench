# -*- coding: utf-8 -*-
"""
信号发生器控制台：通过 USB CDC 给设备发命令
  输入频率数字(如 1000) -> 设备输出该频率方波 (范围 1~5000Hz)
  输入 u                -> 切回软件 UART（发 Hello CH32）
  输入 q                -> 退出
"""
from . import console

SIGNAL_BAUD = 921600


def run():
    port = console.choose_port()
    if port is None:
        return
    ser = console.open_serial(port, baud=SIGNAL_BAUD)
    print(f"已连接 {port}")
    print("输入 频率数字(1~5000) 发方波；u 切 UART；q 退出\n")

    while True:
        try:
            cmd = input("signal> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue
        if cmd.lower() == 'q':
            break
        if cmd.lower() == 'u':
            ser.write(b"U\n")
            print("-> 切到 UART 模式")
        elif cmd.isdigit():
            ser.write(("S" + cmd + "\n").encode())
            print(f"-> 方波 {cmd} Hz")
        else:
            print("请输入数字频率，或 u / q")

    ser.close()
    print("已退出")
