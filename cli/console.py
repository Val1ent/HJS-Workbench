# -*- coding: utf-8 -*-
"""Cross-platform terminal helpers shared by every CLI flow."""
import os
import time

import serial

import core


def clear_screen():
    """清屏：Windows 用 cls，其他平台用 clear。"""
    os.system("cls" if os.name == "nt" else "clear")


def open_serial(port, baud=115200):
    """打开串口并做好连接准备：置 DTR/RTS、等待 0.5s、清空输入缓冲，返回串口对象。"""
    ser = serial.Serial(port, baud, timeout=0)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    return ser


def read_int(prompt, default=None):
    """读取一个整数：回车返回 default，非法输入返回 None，不抛 ValueError。"""
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return None


def choose_port():
    """列出串口并让用户选择；回车重扫，q 返回 None，其余非法输入重新提示。"""
    while True:
        ports = core.list_serial_ports()
        if not ports:
            print("没找到串口，检查 USB 连接")
        print("===== 检测到的串口 =====")
        for i, p in enumerate(ports):
            print(f"  [{i}]  {p[0]}   {p[1]}")
        sel = input("选择【底部 USB-FS 口】序号(回车重扫, q退出): ").strip()
        if sel.lower() == "q":
            return None
        if sel == "":
            continue
        try:
            return ports[int(sel)][0]
        except (ValueError, IndexError):
            print("序号无效")


def choose_decoder():
    """列出 DECKS 中的解码器名称与说明，返回所选名称；q 返回 None。"""
    while True:
        names = list(core.DECKS.keys())
        print("===== 可选协议解码器 =====")
        for i, n in enumerate(names):
            print(f"  [{i}]  {n:<10} {core.DECKS[n]['desc']}")
        sel = input("选择解码器序号: ").strip()
        if sel.lower() == "q":
            return None
        try:
            return names[int(sel)]
        except (ValueError, IndexError):
            print("序号无效")


def pause():
    """等待回车后再返回菜单。"""
    input("\n回车返回菜单...")
