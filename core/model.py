# -*- coding: utf-8 -*-
"""
口袋数字调试助手 - 多协议解码公共框架
========================================
不依赖任何第三方库（纯标准库），不碰固件、不烧录。

【采样数据格式（务必遵守）】
  samples : list[int]，每个 int 是一个采样时刻的 8 通道快照（1 字节）
            bit0 = D0(PD0)，bit1 = D1(PD1)，...，bit7 = D7(PD7)
            即某通道电平 = (sample >> ch) & 1
  rate    : int，采样率 Hz（当前 10000）

【统一事件格式 Event】
  dict: {"t": float(秒), "ch": int(通道), "type": str(类型), "text": str(可读文本)}
  解码器必须返回 list[Event]，并按 t 升序。

【解码器约定】
  每个解码器提供两个函数：
    decode_XXX(samples, rate, **通道参数) -> list[Event]
    make_XXX_test(rate) -> list[int]      # 生成已知内容的 8 通道测试样本
  并在 DECKS 里登记（见文件末尾示例）。
"""

CHANNEL_COUNT = 8
DEFAULT_RATE = 10000


def channel_bits(samples, ch):
    """把 8 通道快照样本展开成某一通道的 0/1 序列。"""
    mask = 1 << ch
    return [1 if (b & mask) else 0 for b in samples]


def set_channel(samples, idx, ch, level):
    """在 samples[idx] 上设置某通道电平（用于生成测试波形）。"""
    if level:
        samples[idx] |= (1 << ch)
    else:
        samples[idx] &= ~(1 << ch) & 0xFF
