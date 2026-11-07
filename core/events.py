# -*- coding: utf-8 -*-
"""Unified event construction and merging."""


def event(t, ch, typ, text):
    """构造统一事件。"""
    return {"t": float(t), "ch": int(ch), "type": str(typ), "text": str(text)}


def merge_events(*lists):
    """合并多路事件并按时间排序。"""
    out = []
    for L in lists:
        out.extend(L)
    out.sort(key=lambda e: e["t"])
    return out
