# -*- coding: utf-8 -*-
"""Capture file support: .sr/.bin read, .sr write, rate parsing, unified open.

The sample rate of serial captures and the .sr probe list come from the
current device backend; the CH32 backend produces a byte-identical .sr
file to the previous hard-coded output.
"""
import os
import zipfile

from .hal import current_backend
from .i18n import _


def serial_rate():
    """Current backend sample rate in Hz."""
    return current_backend().capabilities.sample_rate


def format_rate(rate):
    """Format a rate in Hz the way sigrok metadata expects ('10 kHz')."""
    if rate and rate % 1000 == 0:
        return "{} kHz".format(int(rate // 1000))
    return "{} Hz".format(int(rate))


def parse_rate_str(s):
    """Convert strings like '10 kHz' / '1 MHz' / '1000' to a sample-rate
value in Hz."""
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
    """Read a sigrok .sr zip archive (the capture3.py output format)
-> (rate, samples)."""
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
    """Read a raw one-byte-per-sample channel stream -> (rate, samples)."""
    with open(path, "rb") as f:
        data = f.read()
    return rate, list(data)


def write_sr(path, data, channel_count=None, channel_names=None):
    """Write a sigrok .sr zip archive.

    The probe list, sample rate, and unit size default to the current
    backend's capabilities; ``channel_count``/``channel_names`` may be
    passed explicitly but must still match the backend's real
    capabilities (any other value raises instead of being fabricated).
    For the CH32 backend the default output is byte-identical to the
    previous .sr format.
    """
    caps = current_backend().capabilities
    count = caps.channel_count if channel_count is None else channel_count
    names = list(caps.channel_names if channel_names is None
                 else channel_names)
    current_backend().validate_config(channels=count)
    if len(names) != count:
        raise ValueError(
            _("Channel names do not match the channel count ({names} names, "
              "{count} channels).").format(names=len(names), count=count))
    if channel_names is not None and list(channel_names) != list(
            caps.channel_names):
        raise ValueError(
            _("Unsupported channel names for the {name} backend: {names}"
              ).format(name=caps.display_name,
                       names=", ".join(str(n) for n in channel_names)))
    metadata = (
        "[global]\nsigrok version=0.7.2\n\n[device 1]\n"
        "capturefile=logic-1\n"
        "total probes={count}\n"
        "samplerate={rate}\n"
        "total analog=0\n"
        + "".join("probe{index}={name}\n".format(
            index=i + 1, name=names[i]) for i in range(count))
        + "unitsize={unit}\n".format(unit=caps.unit_size)
    ).format(count=count, rate=format_rate(caps.sample_rate))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("version", "2")
        z.writestr("metadata", metadata)
        z.writestr("logic-1", bytes(data))


def acquire_file(path):
    """Read a .sr / .bin capture file; return (rate, samples).

    .sr is a sigrok zip archive (sample rate read from its metadata);
    .bin is a raw one-byte-per-sample channel stream (sample rate uses
    the current backend's sample rate).
    Other extensions or read failures raise an exception with a readable
    message.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".sr", ".bin"):
        raise ValueError(
            _("Unsupported file type: {ext}. Please choose a .sr or .bin file."
              ).format(ext=ext or "(no extension)"))
    try:
        if ext == ".sr":
            rate, samples = read_sr(path)
        else:
            rate, samples = read_bin(path, serial_rate())
    except Exception as exc:
        raise ValueError(
            _("Cannot read file {path}: {error}").format(path=path, error=exc)
        ) from exc
    if rate is None:
        raise ValueError(
            _("Cannot read file {path}: the file has no sample-rate "
              "information.").format(path=path))
    return rate, list(samples)
