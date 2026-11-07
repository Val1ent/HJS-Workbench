# -*- coding: utf-8 -*-
"""Decoder registry and self-test helpers."""

# ----------------------------------------------------------------------
# 注册表与自测
# ----------------------------------------------------------------------
DECKS = {}   # name -> {"decode": fn, "make": fn, "desc": str}


def register(name, decode_fn, make_fn, desc=""):
    DECKS[name] = {"decode": decode_fn, "make": make_fn, "desc": desc}


def print_events(events, ch_name=None):
    """终端打印事件。"""
    if not events:
        print("  (未解码出任何事件)")
    for e in events:
        c = ch_name if ch_name is not None else e["ch"]
        print(f"  {e['t']*1000:9.3f} ms  D{c}  {e['type']:<10} {e['text']}")


def selftest(name):
    """对某个解码器跑自带测试波形，返回 (事件, 样本)。"""
    deck = DECKS[name]
    samples = deck["make"](10000)
    events = deck["decode"](samples, 10000)
    return events, samples
