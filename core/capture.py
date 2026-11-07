# -*- coding: utf-8 -*-
"""Serial port enumeration and one-shot serial acquisition."""
import time

import serial
from serial.tools import list_ports

from .files import SERIAL_RATE


def list_serial_ports():
    """返回可用串口列表 [(设备名, 描述), ...]。"""
    return [(p.device, p.description) for p in list_ports.comports()]


def acquire_serial(port, n_points, timeout=8.0):
    """从指定串口单次采集恰好 n_points 个字节。

    打开串口后置 DTR/RTS，短暂等待并清空输入缓冲，随后非阻塞轮询，
    累计读到 n_points 个字节或超时为止；结束（含异常）时关闭串口。
    超时未读满时抛出带排查建议的异常。
    """
    ser = serial.Serial(port, 115200, timeout=0)
    ser.dtr = True
    ser.rts = True
    try:
        time.sleep(0.5)
        ser.reset_input_buffer()
        data = bytearray()
        deadline = time.monotonic() + timeout
        while len(data) < n_points and time.monotonic() < deadline:
            pending = ser.in_waiting
            if pending:
                data.extend(ser.read(min(pending, n_points - len(data))))
            else:
                time.sleep(0.01)
    finally:
        ser.close()
    if len(data) < n_points:
        raise RuntimeError(
            f"采集超时：实际收到 {len(data)} 点，需要 {n_points} 点。\n"
            "请检查：是否选择了 CH32 数据口（底部 USB-FS 口而非调试口）、"
            "A15 是否环回到 D0、该串口是否被其他程序占用，然后重试。"
        )
    return SERIAL_RATE, list(data)
