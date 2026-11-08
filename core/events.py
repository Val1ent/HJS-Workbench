# -*- coding: utf-8 -*-
"""Unified event construction and merging."""


def event(t, ch, typ, text):
    """Build a unified event."""
    return {"t": float(t), "ch": int(ch), "type": str(typ), "text": str(text)}


def merge_events(*lists):
    """Merge multiple event lists and sort them by time."""
    out = []
    for L in lists:
        out.extend(L)
    out.sort(key=lambda e: e["t"])
    return out
