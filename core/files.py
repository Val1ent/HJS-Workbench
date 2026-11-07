# -*- coding: utf-8 -*-
"""Capture file support: .sr/.bin read, .sr write, rate parsing, unified open."""
import os
import zipfile

SERIAL_RATE = 10000


def parse_rate_str(s):
    """'10 kHz' / '1 MHz' / '1000' 之类的字符串 → 采样率 Hz 数值。"""
    s = str(s).strip().lower()
    num = ""
    for ch in s:
        if ch.isdigit() or ch == ".":
            num += ch
        else:
            break
    if not num:
        return None
    val = float(num)
    if "mhz" in s:
        val *= 1e6
    elif "khz" in s:
        val *= 1e3
    return int(round(val))


def read_sr(path):
    """读取 sigrok .sr 压缩包（capture3.py 的输出格式）→ (rate, samples)。"""
    with zipfile.ZipFile(path) as z:
        meta = z.read("metadata").decode("utf-8", "replace")
        rate = None
        for line in meta.splitlines():
            line = line.strip()
            if line.startswith("samplerate="):
                rate = parse_rate_str(line.split("=", 1)[1])
        data = z.read("logic-1")
    return rate, list(data)


def read_bin(path, rate):
    """读取原始 8 通道字节流 → (rate, samples)。"""
    with open(path, "rb") as f:
        data = f.read()
    return rate, list(data)


RATE_STR = "10 kHz"


def write_sr(path, data):
    metadata = (
        "[global]\nsigrok version=0.7.2\n\n[device 1]\n"
        "capturefile=logic-1\n"
        "total probes=8\n"
        f"samplerate={RATE_STR}\n"
        "total analog=0\n"
        "probe1=D0\nprobe2=D1\nprobe3=D2\nprobe4=D3\n"
        "probe5=D4\nprobe6=D5\nprobe7=D6\nprobe8=D7\n"
        "unitsize=1\n"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("version", "2")
        z.writestr("metadata", metadata)
        z.writestr("logic-1", bytes(data))


def acquire_file(path):
    """读取 .sr / .bin 采集文件，返回 (rate, samples)。

    .sr 为 sigrok 压缩包（采样率从 metadata 读取）；
    .bin 为原始 8 通道字节流（采样率按固件值 10000 Hz）。
    其他扩展名或读取失败时抛出带可读信息的异常。
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".sr", ".bin"):
        raise ValueError(
            f"不支持的文件类型：{ext or '（无扩展名）'}。请选择 .sr 或 .bin 文件。"
        )
    try:
        if ext == ".sr":
            rate, samples = read_sr(path)
        else:
            rate, samples = read_bin(path, SERIAL_RATE)
    except Exception as exc:
        raise ValueError(f"无法读取文件 {path}：{exc}") from exc
    if rate is None:
        raise ValueError(f"无法读取文件 {path}：文件中缺少采样率信息。")
    return rate, list(samples)
