# -*- coding: utf-8 -*-
"""
Offline tools submenu: self-test report, PPM verification, CSV export,
pulse statistics, dual-waveform diff, HTML waveform export, and file
analysis (the offline capabilities of proto_lab / proto_stats /
proto_diff / proto_browser).
"""
import csv
import json
import os
import statistics

import core
from core.decoders.servo import decode_servo
from core.i18n import _
from core.model import channel_bits
from core.segments import build_wave, pulse_widths

from . import console


def _default_rate():
    """Sample rate of the current device backend, in Hz."""
    return core.current_backend().capabilities.sample_rate


def _channel_count():
    """Channel count of the current device backend."""
    return core.current_backend().capabilities.channel_count


def _channel_names():
    """Channel names of the current device backend."""
    return list(core.current_backend().capabilities.channel_names)

# ---- Acceptance rules: (type, key content) pairs that must appear in the
# ---- self-test events ----
REQUIRED = {
    "nec":        [("LEADER", None), ("NEC", "addr=0x00 cmd=0x45"), ("REPEAT", None)],
    "servo":      [("SERVO", "angle=0.0 deg"), ("SERVO", "angle=90.0 deg"),
                   ("SERVO", "angle=180.0 deg")],
    "i2c":        [("START", None), ("ADDR", "0x48 W ACK"),
                   ("DATA", "0x55 ACK"), ("STOP", None)],
    "spi":        [("CS_LOW", None), ("SPI", "MOSI=0x3C MISO=0x11"),
                   ("SPI", "MOSI=0xA5 MISO=0x22"), ("CS_HIGH", None)],
    "stepper":    [("STEP", "step #1"), ("STEP_SUM", "total 40 steps"), ("STEP_SUM", "pos=+20")],
    "encoder":    [("ENCODER", None), ("ZERO", None)],
    "rc5":        [("RC5", "addr=5 cmd=33")],
    "ultrasonic": [("TRIG", None), ("DISTANCE", "distance=17.0cm"),
                   ("DISTANCE", "distance=25.5cm")],
    "fan":        [("FAN", None), ("FAN_SUM", "avg=3000RPM")],
    "dht11":      [("DHT11_START", None), ("DHT11_RESPONSE", None),
                   ("DHT11", "humidity=45.0% temperature=25.0C")],
    "onewire":    [("RESET", None), ("PRESENCE", None), ("ROM", "0xCC"),
                   ("CMD", "0xBE"), ("SCRATCHPAD", "90 01 4B 46 7F FF FF FF 57"),
                   ("TEMP", "temp=25.0C CRC OK")],
    "swd":        [("SWD_RESET", "line reset"), ("SWD_WRITE", "data=0x12345678"),
                   ("SWD_READ", "data=0x87654321")],
    "modbus":     [("MODBUS", "addr=1 read holding registers start=0 qty=2 CRC OK")],
    "wiegand":    [("WIEGAND_BIT", "bit=0"),
                   ("WIEGAND_FRAME", "facility=101 card=12345 parity OK")],
    "hd44780":    [("CMD", "0x28"), ("CMD", "0x0C"), ("CHAR", "'H'"),
                   ("CHAR", "'i'")],
    "sirc":       [("SIRC", "dev=1 cmd=22 (12 bits)")],
    "ds1302":     [("DS1302_WRITE", "seconds"), ("DS1302_READ", "hours"),
                   ("TIME", "time=13:30:45")],
    "manchester": [("MAN_BYTE", "0x48 'H'"), ("MAN_BYTE", "0x69 'i'")],
    "nmea":       [("NMEA", "$GPGGA"), ("NMEA", "checksum OK")],
}
FORBIDDEN = {
    "nec": [("NEC_ERR", None)],        # Not a single NEC checksum error is allowed
    "dht11": [("DHT11_ERR", None)],
    "onewire": [("TEMP_ERR", None)],
    "modbus": [("MODBUS_CRC_ERR", None)],
    "wiegand": [("WIEGAND_PARITY_ERR", None)],
    "nmea": [("NMEA_ERR", None)],
}


def check_deck(name, events):
    """Check events against REQUIRED/FORBIDDEN; return (ok, problem list)."""
    problems = []
    for typ, sub in REQUIRED.get(name, []):
        hits = [e for e in events if e["type"] == typ
                and (sub is None or sub in e["text"])]
        if not hits:
            problems.append(f"missing {typ} {sub or ''}".strip())
    for typ, sub in FORBIDDEN.get(name, []):
        hits = [e for e in events if e["type"] == typ
                and (sub is None or sub in e["text"])]
        if hits:
            problems.append(f"forbidden item present {typ} x{len(hits)}")
    return (len(problems) == 0), problems


def report_all():
    """Run the self-test of every registered decoder, check expectations,
    and print the acceptance report. Returns whether all passed.

The banner wording is translated; the report body (decoder names, event
text, PASS/FAIL rows and the acceptance summary) is data output and stays
English in every language.
"""
    print("=" * 64)
    print(_("Full protocol self-test report (fully offline - zero flashing - repeatable acceptance)"))
    print("=" * 64)
    passed = 0
    total = 0
    rate = _default_rate()
    for name, deck in core.DECKS.items():
        total += 1
        try:
            samples = deck["make"](rate)
            events = deck["decode"](samples, rate)
            ok, problems = check_deck(name, events)
        except Exception as exc:
            ok, problems, events = False, [f"error: {exc}"], []
        if ok:
            passed += 1
        print(f"\n[{'PASS' if ok else 'FAIL'}] {name:<10} {deck['desc']}"
              f"  events {len(events)}")
        for p in problems:
            print("        problem: " + p)
        for e in events[:5]:
            print(f"        {e['t']*1000:8.3f}ms  {e['type']:<10} {e['text']}")
        if len(events) > 5:
            print(f"        ... {len(events)-5} more omitted")
    print("\n" + "=" * 64)
    print(f"Acceptance: {passed}/{total} passed" + ("  [OK]" if passed == total else "  [FAIL]"))
    return passed == total


def make_ppm_test(rate):
    """PPM demo: all channel gaps 1000-1800us in order, frame sync > 4000us."""
    n = int(0.06 * rate)
    pulses = []
    t = 0.003
    for us in (1000, 1200, 1400, 1600, 1800, 1500, 1300, 1100):
        pulses.append((t, 1, 0.0004))       # 400us channel pulse
        t += us / 1e6
    pulses.append((t, 1, 0.0004))           # Short end-of-frame pulse completes the 8th channel value
    return build_wave(0, pulses, rate, n, idle=0)


def check_ppm():
    """Verify the PPM branch of decode_servo: an all-channel frame and no
false SERVO events."""
    rate = _default_rate()
    samples = make_ppm_test(rate)
    events = decode_servo(samples, rate, ch=0)
    ppm = [e for e in events if e["type"] == "PPM"]
    servos = [e for e in events if e["type"] == "SERVO"]
    ok = len(ppm) == 1 and "8 ch" in ppm[0]["text"] and not servos
    print("=" * 64)
    print(f"[{'PASS' if ok else 'FAIL'}] PPM multi-channel extension check")
    for e in events:
        print(f"  {e['t']*1000:9.3f} ms  D{e['ch']}  {e['type']:<10} {e['text']}")
    print(_("Note: the in-frame channel gaps are recognized as PPM and not misreported as SERVO (gaps != 20 ms)."))
    return ok


def export_csv():
    """Export all decoder self-test events to CSV (utf-8-sig, opens directly in Excel)."""
    path = os.path.join(os.getcwd(), "proto_lab_events.csv")
    rate = _default_rate()
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Decoder", "Type", "Time ms", "Channel", "Content"])
        for name in core.DECKS:
            samples = core.DECKS[name]["make"](rate)
            for e in core.DECKS[name]["decode"](samples, rate):
                w.writerow([name, e["type"], f"{e['t']*1000:.3f}",
                            f"D{e['ch']}", e["text"]])
    print(_("Exported: {path}").format(path=path))


# ----------------------------------------------------------------------
# Pulse statistics and glitch detection (matches proto_stats.py)
# ----------------------------------------------------------------------
BINS_MS = [(0, 0.1), (0.1, 0.2), (0.2, 0.5), (0.5, 1), (1, 2), (2, 5),
           (5, 10), (10, 20), (20, 50), (50, 1e9)]
BIN_LABEL = ["<0.1ms", "0.1~0.2", "0.2~0.5", "0.5~1", "1~2", "2~5",
             "5~10", "10~20", "20~50", ">=50"]


def load(path, rate):
    """Read a .sr or .bin file -> (rate, samples)."""
    if path.lower().endswith(".sr"):
        r, s = core.read_sr(path)
        if rate:
            r = rate
        return r, s
    r = rate or _default_rate()
    return r, core.read_bin(path, r)[1]


def analyze(bits, rate, glitch_s):
    """Single-channel health check; return a metrics dict."""
    n = len(bits)
    dt = 1.0 / rate
    segs = pulse_widths(bits, rate)     # [(start, level, width_s), ...]
    rises = [i for i in range(1, n) if bits[i - 1] == 0 and bits[i] == 1]
    falls = [i for i in range(1, n) if bits[i - 1] == 1 and bits[i] == 0]
    edges = len(rises) + len(falls)
    freq = None
    duty = None
    if len(rises) >= 2:
        per = statistics.mean([rises[k + 1] - rises[k]
                               for k in range(len(rises) - 1)]) * dt
        if per > 0:
            freq = 1.0 / per
            highs = []
            fi = 0
            for r in rises:
                while fi < len(falls) and falls[fi] <= r:
                    fi += 1
                if fi < len(falls):
                    highs.append(falls[fi] - r)
            if highs:
                duty = statistics.mean(highs) * dt / per * 100.0
    # Width statistics: drop the first and last segments that may be truncated
    body = segs[1:-1] if len(segs) >= 3 else segs
    widths = [w for (_, _, w) in body]
    stats = None
    if widths:
        stats = {"min": min(widths), "max": max(widths),
                 "mean": statistics.mean(widths),
                 "median": statistics.median(widths), "count": len(widths)}
    # Histogram
    hist = [0] * len(BINS_MS)
    for w in widths:
        for bi, (lo, hi) in enumerate(BINS_MS):
            if lo * 1e-3 <= w < hi * 1e-3:
                hist[bi] += 1
                break
    # Glitches: pulses narrower than the threshold
    glitches = [(s, lvl, w) for (s, lvl, w) in body if w < glitch_s]
    return {"edges": edges, "freq": freq, "duty": duty, "stats": stats,
            "hist": hist, "glitches": glitches}


def report_channel(ch, res, rate, glitch_s):
    print(f"\n---- D{ch} ----")
    if res["edges"] == 0:
        print(_("  Silent: no transitions in the whole segment (likely floating / constant level / not wired)"))
        return
    parts = [_("  transitions {edges}").format(edges=res["edges"])]
    if res["freq"]:
        parts.append(_("freq~{freq:.1f} Hz").format(freq=res["freq"]))
    if res["duty"] is not None:
        parts.append(_("duty~{duty:.1f}%").format(duty=res["duty"]))
    print(" | ".join(parts))
    s = res["stats"]
    if s:
        print(_("  Pulse width: min {mn:.0f}us | median {median:.0f}us | "
                "mean {mean:.0f}us | max {mx:.0f}us ({count} segments)").format(
                    mn=s['min']*1e6, median=s['median']*1e6,
                    mean=s['mean']*1e6, mx=s['max']*1e6, count=s['count']))
    mx = max(res["hist"]) or 1
    print(_("  Width histogram:"))
    for bi in range(len(BINS_MS)):
        c = res["hist"][bi]
        if c:
            print(f"    {BIN_LABEL[bi]:>8} {c:4d}  {'█' * max(1, int(c / mx * 36))}")
    if res["glitches"]:
        print(_("  [!] Glitches (< {us:.0f}us): {n} found:").format(
            us=glitch_s*1e6, n=len(res['glitches'])))
        for (s_i, lvl, w) in res["glitches"][:12]:
            print(_("    {ms:8.3f} ms  width {w:.0f}us  level={lvl}").format(
                ms=s_i / rate * 1000, w=w*1e6, lvl=lvl))
        if len(res["glitches"]) > 12:
            print(_("    ... the other {n} are in the CSV").format(
                n=len(res['glitches'])-12))
    else:
        print(_("  Glitches: none (threshold {us:.0f}us)").format(us=glitch_s*1e6))


def pulse_stats():
    """Interactive pulse statistics and glitch detection (matches proto_stats.py main)."""
    path = input(_("Capture file path (.sr/.bin), Enter to use a decoder demo waveform: ")).strip()
    dflt = _default_rate()
    if path:
        raw_rate = console.read_int(_("Sample rate in Hz (Enter defaults to {rate}): ").format(rate=dflt), dflt)
        rate = raw_rate if raw_rate is not None else dflt
        r, samples = load(path, rate)
        rate = r
        src = path
    else:
        deck_name = console.choose_decoder()
        if deck_name is None:
            return
        rate = console.read_int(_("Sample rate in Hz (Enter defaults to {rate}): ").format(rate=dflt), dflt)
        if rate is None:
            rate = dflt
        samples = core.DECKS[deck_name]["make"](rate)
        src = f"demo waveform {deck_name} ({core.DECKS[deck_name]['desc']})"

    raw = input(_("Glitch threshold us (Enter defaults to 200): ")).strip()
    try:
        glitch_us = float(raw) if raw else 200.0
    except ValueError:
        glitch_us = 200.0
    raw = input(_("Channel list (comma-separated, Enter defaults to all): ")).strip()
    if raw:
        try:
            chs = [int(x) for x in raw.split(",")]
        except ValueError:
            print(_("Invalid channel list, using all channels"))
            chs = list(range(_channel_count()))
    else:
        chs = list(range(_channel_count()))
    out = input(_("CSV output path (Enter defaults to proto_stats_report.csv): ")).strip() \
        or os.path.join(os.getcwd(), "proto_stats_report.csv")

    glitch_s = glitch_us * 1e-6
    print("=" * 64)
    print(_("Pulse statistics and glitch detection  |  {src}").format(src=src))
    print(_("Sample rate {rate} Hz - {n} points ({ms:.1f} ms) - glitch threshold {us:.0f}us").format(
        rate=rate, n=len(samples), ms=len(samples)/rate*1000, us=glitch_us))
    results = {}
    for ch in chs:
        res = analyze(channel_bits(samples, ch), rate, glitch_s)
        results[ch] = res
        report_channel(ch, res, rate, glitch_s)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Channel", "Category", "Time ms", "Value", "Notes"])
        for ch in chs:
            r = results[ch]
            s = r["stats"]
            w.writerow([f"D{ch}", "SUMMARY", "", f"{r['edges']}", "edge count"])
            if r["freq"]:
                w.writerow([f"D{ch}", "SUMMARY", "", f"{r['freq']:.2f}", "mean frequency Hz"])
            if r["duty"] is not None:
                w.writerow([f"D{ch}", "SUMMARY", "", f"{r['duty']:.2f}", "mean duty %"])
            if s:
                w.writerow([f"D{ch}", "SUMMARY", "", f"{s['min']*1e6:.0f}", "min pulse width us"])
                w.writerow([f"D{ch}", "SUMMARY", "", f"{s['max']*1e6:.0f}", "max pulse width us"])
            for (s_i, lvl, wd) in r["glitches"]:
                w.writerow([f"D{ch}", "GLITCH", f"{s_i/rate*1000:.3f}",
                            f"{wd*1e6:.0f}us", f"level={lvl}"])
    print(_("\nReport exported: {out}").format(out=out))


# ----------------------------------------------------------------------
# Dual-waveform diff (matches proto_diff.py)
# ----------------------------------------------------------------------
def diff_segments(a_bits, b_bits):
    """Return the differing intervals [(start, end_exclusive), ...]."""
    segs = []
    start = None
    for i in range(len(a_bits)):
        if a_bits[i] != b_bits[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                segs.append((start, i))
                start = None
    if start is not None:
        segs.append((start, len(a_bits)))
    return segs


def run_diff(path_a, path_b, rate=None, csv_path=None):
    r, A = load(path_a, rate)
    _, B = load(path_b, rate)
    n = min(len(A), len(B))
    dt = 1.0 / r
    print("=" * 64)
    print(_("Dual-waveform diff report (A=reference, B=device under test)"))
    print(f"A = {path_a}  ({len(A)} points)")
    print(f"B = {path_b}  ({len(B)} points)")
    if len(A) != len(B):
        print(_("Different lengths: comparing only the overlapping {n} points").format(n=n))
    print("=" * 64)

    first_global = None
    per = []
    nch = _channel_count()
    for ch in range(nch):
        ab = channel_bits(A, ch)[:n]
        bb = channel_bits(B, ch)[:n]
        segs = diff_segments(ab, bb)
        cnt = sum(e - s for (s, e) in segs)
        if cnt and (first_global is None or segs[0][0] < first_global):
            first_global = segs[0][0]
        per.append((ch, cnt, segs))

    total = sum(c for (_, c, _) in per)
    sim = 100.0 * (1.0 - total / (n * float(nch))) if n else 100.0
    print(f"\nOverall similarity: {sim:.4f}%   differing sample points: {total} / {n * nch}")
    if first_global is not None:
        print(f"First difference: {first_global * dt * 1000:.3f} ms (point {first_global})")
    print("\nChannel  Diff points  Share  Diff intervals")
    for (ch, cnt, segs) in per:
        print(f"  D{ch}    {cnt:7d}   {cnt / n * 100:6.2f}%    {len(segs):6d}")

    # ASCII comparison band around the first difference
    if first_global is not None:
        w = 80
        lo = max(0, first_global - w // 2)
        hi = min(n, lo + w)
        print(_("\n-- Local comparison (points {lo}-{hi}, █=high _=low ^=diff) --").format(
            lo=lo, hi=hi))
        for ch in range(nch):
            ab = channel_bits(A, ch)[:n]
            bb = channel_bits(B, ch)[:n]
            la = "".join("█" if ab[i] else "_" for i in range(lo, hi))
            lb = "".join("█" if bb[i] else "_" for i in range(lo, hi))
            mark = "".join("^" if ab[i] != bb[i] else " " for i in range(lo, hi))
            if mark.strip():
                print(f"D{ch} A {la}\n    B {lb}\n      {mark}")

    # CSV diff list
    out = csv_path or os.path.join(os.getcwd(), "proto_diff_report.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        wcsv = csv.writer(f)
        wcsv.writerow(["Channel", "Start ms", "End ms", "Diff points"])
        for (ch, cnt, segs) in per:
            for (s, e) in segs:
                wcsv.writerow([f"D{ch}", f"{s * dt * 1000:.3f}",
                               f"{e * dt * 1000:.3f}", e - s])
    print(_("\nDiff interval list exported: {out}").format(out=out))
    return sim


def diff_flow():
    """Interactive dual-waveform diff (matches proto_diff.py main)."""
    path_a = input(_("Reference waveform A path (.sr/.bin): ")).strip()
    if not path_a:
        return
    path_b = input(_("Waveform B under test path (.sr/.bin): ")).strip()
    if not path_b:
        return
    raw = input(_("Sample rate (.bin only, Enter for auto): ")).strip()
    rate = None
    if raw:
        try:
            rate = int(raw)
        except ValueError:
            rate = None
    csv_path = input(_("CSV output path (Enter defaults to proto_diff_report.csv): ")).strip() or None
    run_diff(path_a, path_b, rate, csv_path)


# ----------------------------------------------------------------------
# Interactive waveform browser export (matches proto_browser.py)
# ----------------------------------------------------------------------
TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>@@TITLE@@</title>
<style>
body{margin:0;background:#0b0f14;color:#d7e2ee;font-family:Consolas,'Microsoft YaHei',monospace}
#bar{padding:8px 12px;background:#11161d;border-bottom:1px solid #26313d;font-size:14px}
#cv{display:block}
#info{padding:6px 12px;font-size:12px;color:#8fb0cc;background:#0e1319}
#events{padding:6px 12px;font-size:12px}
#events .ev{border-bottom:1px dotted #22303c;padding:1px 0;cursor:pointer}
#events .ev:hover{background:#14202b}
#events .t{color:#fbbf24;display:inline-block;width:88px}
table{border-collapse:collapse;margin:8px 12px;font-size:12px}
td,th{border:1px solid #26313d;padding:3px 10px}
th{background:#11161d;color:#8fb0cc}
</style>
</head>
<body>
<div id="bar"><b>@@TITLE@@</b> | wheel zoom - drag to pan - click = cursor A - Shift+click = cursor B</div>
<canvas id="cv" width="1200" height="260"></canvas>
<div id="info"></div>
<div id="events"></div>
<div id="stats">@@STATS@@</div>
<script>
var RATE=@@RATE@@, SAMPLES=@@SAMPLES@@, EVENTS=@@EVENTS@@;
var cv=document.getElementById('cv'), cx=cv.getContext('2d');
var W=cv.width, H=cv.height, TOP=24, ROWH=(H-TOP)/8;
var v0=0, spp=Math.max(1,Math.ceil(SAMPLES.length/W));
var curA=null, curB=null, drag=null;
function idxToX(i){return (i-v0)/spp;}
function draw(){
  cx.fillStyle='#0b0f14'; cx.fillRect(0,0,W,H);
  cx.strokeStyle='#1c2733';
  for(var g=0;g<8;g++){cx.beginPath();cx.moveTo(0,TOP+g*ROWH+0.5);cx.lineTo(W,TOP+g*ROWH+0.5);cx.stroke();}
  var v1=Math.min(SAMPLES.length, v0+Math.ceil(spp*W));
  var w=Math.min(W, Math.ceil((v1-v0)/spp));
  cx.font='12px Consolas,monospace';
  for(var ch=0;ch<8;ch++){
    cx.fillStyle='#7f95a8'; cx.fillText('D'+ch,2,TOP+ch*ROWH+15);
    var y=TOP+ch*ROWH, prev=-1, seg=0;
    for(var px=0;px<w;px++){
      var lv=(SAMPLES[v0+Math.floor(px*spp)]>>ch)&1;
      if(lv!==prev){
        if(prev===1){cx.fillStyle='#3ecf8e';cx.fillRect(seg,y+4,px-seg,ROWH-10);}
        prev=lv; seg=px;
      }
    }
    if(prev===1){cx.fillStyle='#3ecf8e';cx.fillRect(seg,y+4,w-seg,ROWH-10);}
  }
  cx.fillStyle='rgba(251,191,36,0.7)';
  for(var k=0;k<EVENTS.length;k++){
    var ii=Math.round(EVENTS[k].t*RATE);
    if(ii>=v0&&ii<=v1){cx.fillRect(idxToX(ii),2,1,H-4);}
  }
  if(curA!==null){cx.strokeStyle='#f87171';cx.beginPath();cx.moveTo(idxToX(curA),0);cx.lineTo(idxToX(curA),H);cx.stroke();}
  if(curB!==null){cx.strokeStyle='#38bdf8';cx.beginPath();cx.moveTo(idxToX(curB),0);cx.lineTo(idxToX(curB),H);cx.stroke();}
  var msg='view '+v0+'~'+v1+' / '+SAMPLES.length+' points - '+spp.toFixed(2)+' points/pixel';
  if(curA!==null){msg+='  |  A@'+((curA/RATE)*1000).toFixed(3)+'ms';}
  if(curB!==null){msg+='  |  B@'+((curB/RATE)*1000).toFixed(3)+'ms';}
  if(curA!==null&&curB!==null){msg+='  |  dt='+(Math.abs(curB-curA)/RATE*1000).toFixed(3)+'ms';}
  document.getElementById('info').textContent=msg;
}
cv.addEventListener('wheel',function(ev){ev.preventDefault();
  var c=v0+ev.offsetX*spp;
  spp=Math.max(1,Math.min(64, spp*(ev.deltaY>0?1.3:0.77)));
  v0=Math.max(0,Math.min(SAMPLES.length-1, c-ev.offsetX*spp));
  draw();});
cv.addEventListener('mousedown',function(ev){drag={x:ev.offsetX,v0:v0,moved:false};});
window.addEventListener('mouseup',function(){drag=null;});
cv.addEventListener('mousemove',function(ev){
  if(!drag)return;
  drag.moved=true;
  v0=Math.max(0,Math.min(SAMPLES.length-1, drag.v0-(ev.offsetX-drag.x)*spp));
  draw();});
cv.addEventListener('click',function(ev){
  if(drag&&drag.moved){return;}
  var ii=Math.floor(v0+ev.offsetX*spp);
  if(ii<0||ii>=SAMPLES.length)return;
  if(ev.shiftKey){curB=ii;}else{curA=ii;}
  draw();});
function jump(i){v0=Math.max(0,Math.min(SAMPLES.length-1,i-W*spp/2));draw();}
(function(){
  var box=document.getElementById('events');
  if(!EVENTS.length){box.innerHTML='<div style="color:#5b6f83;padding:4px 0">No decoded events (no decoder overlaid)</div>';return;}
  var n=Math.min(EVENTS.length,300), html='<div style="padding:4px 0;color:#8fb0cc">Decoded events (first '+n+', click to jump):</div>';
  for(var i=0;i<n;i++){
    var e=EVENTS[i];
    var tx=String(e.text).replace(/</g,'&lt;').replace(/>/g,'&gt;');
    var ty=String(e.type).replace(/</g,'&lt;').replace(/>/g,'&gt;');
    html+='<div class="ev" onclick="jump('+Math.round(e.t*RATE)+')">'+
      '<span class="t">'+(e.t*1000).toFixed(3)+'ms</span>D'+e.ch+' <b>['+ty+']</b> '+tx+'</div>';
  }
  box.innerHTML=html;
})();
draw();
</script>
</body>
</html>
"""


def build_html(title, rate, samples, events):
    """Build a single-file HTML report."""
    # Per-channel statistics
    stats_rows = []
    nch = _channel_count()
    for ch in range(nch):
        bits = channel_bits(samples, ch)
        rises = [i for i in range(1, len(bits)) if bits[i - 1] == 0 and bits[i] == 1]
        falls = [i for i in range(1, len(bits)) if bits[i - 1] == 1 and bits[i] == 0]
        edges = len(rises) + len(falls)
        freq_txt = duty_txt = "--"
        if len(rises) >= 2:
            per = statistics.mean([rises[k + 1] - rises[k]
                                   for k in range(len(rises) - 1)]) / rate
            if per > 0:
                freq_txt = f"{1.0 / per:.1f} Hz"
                highs = []
                fi = 0
                for r in rises:
                    while fi < len(falls) and falls[fi] <= r:
                        fi += 1
                    if fi < len(falls):
                        highs.append(falls[fi] - r)
                if highs:
                    duty_txt = f"{statistics.mean(highs) / rate / per * 100:.1f}%"
        stats_rows.append(f"<tr><td>D{ch}</td><td>{freq_txt}</td>"
                          f"<td>{duty_txt}</td><td>{edges}</td></tr>")
    stats_html = ("<table><tr><th>Channel</th><th>Mean frequency</th><th>Mean duty</th>"
                  "<th>Edge count</th></tr>" + "".join(stats_rows) + "</table>")

    title_safe = title.replace("&", "&amp;").replace("<", "&lt;")
    info = (f"Sample rate {rate} Hz - {len(samples)} points - "
            f"duration {len(samples) / rate * 1000:.1f} ms - events {len(events)}")
    js_events = json.dumps([{"t": e["t"], "ch": e["ch"], "type": e["type"],
                             "text": e["text"]} for e in events],
                           ensure_ascii=False)
    js_samples = json.dumps(samples)
    return (TEMPLATE
            .replace("@@TITLE@@", title_safe)
            .replace("@@INFO@@", info)
            .replace("@@RATE@@", str(rate))
            .replace("@@SAMPLES@@", js_samples)
            .replace("@@EVENTS@@", js_events)
            .replace("@@STATS@@", stats_html))


def html_export():
    """Interactive single-file HTML waveform export (matches proto_browser.py main)."""
    path = input(_("Capture file path (.sr/.bin), Enter to use a decoder demo waveform: ")).strip()
    if path:
        r, samples = load(path, None)
        rate = r
        dec_name = input(_("Overlay decoder name (Enter to skip): ")).strip()
        events = []
        if dec_name:
            if dec_name not in core.DECKS:
                print(_("Unknown decoder:"), dec_name, _("available:"), list(core.DECKS))
                return
            try:
                events = core.DECKS[dec_name]["decode"](samples, rate)
            except Exception as exc:
                print(_("Decode failed (ignored):"), exc)
        title = f"{os.path.basename(path)} - {rate} Hz"
    else:
        deck_name = console.choose_decoder()
        if deck_name is None:
            return
        dflt = _default_rate()
        rate = console.read_int(_("Sample rate in Hz (Enter defaults to {rate}): ").format(rate=dflt), dflt)
        if rate is None:
            rate = dflt
        samples = core.DECKS[deck_name]["make"](rate)
        events = core.DECKS[deck_name]["decode"](samples, rate)
        title = f"{deck_name} - {core.DECKS[deck_name]['desc']} demo waveform"

    out = input(_("Output file (Enter defaults to proto_wave.html): ")).strip() \
        or os.path.join(os.getcwd(), "proto_wave.html")
    html = build_html(title, rate, samples, events)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(_("Created: {out}  ({bytes} bytes)").format(out=out, bytes=os.path.getsize(out)))
    ans = input(_("Open the browser automatically after generation? (Enter=yes, n=no): ")).strip().lower()
    if ans != "n":
        try:
            os.startfile(out)
        except Exception:
            print(_("(Could not open automatically; double-click the file manually)"))


# ----------------------------------------------------------------------
# File analysis: UART decode + first-channel measurement
# ----------------------------------------------------------------------
def file_analysis():
    """Open a capture file and run UART text decoding plus first-channel
measurement."""
    path = input(_("Capture file path (.sr/.bin): ")).strip()
    if not path:
        return
    try:
        rate, samples = core.acquire_file(path)
    except Exception as exc:
        print(_("Read failed:"), exc)
        return
    print(_("Opened: {path}").format(path=path))
    print(_("Sample rate {rate} Hz - {n} points - duration {ms:.1f} ms").format(
        rate=rate, n=len(samples), ms=len(samples)/rate*1000))

    bits = channel_bits(samples, 0)
    frames = core.scan_frames(bits)
    text = "".join(c for _, c in frames)
    print(_("\n-- UART decode ({ch}, 1000bps 8N1) --").format(
        ch=_channel_names()[0]))
    print(_("  Received: {text}").format(
        text=repr(text) if text else "(no complete frame decoded)"))

    m = core.measure(bits, rate)
    print(_("\n-- {ch} measurement --").format(ch=_channel_names()[0]))
    if m:
        print(_("  Frequency      : {freq:.1f} Hz").format(freq=m['freq']))
        print(_("  Period         : {period:.3f} ms  (min {pmin:.3f} / max {pmax:.3f})").format(
            period=m['period']*1000, pmin=m['pmin']*1000, pmax=m['pmax']*1000))
        print(_("  High pulse     : {high:.3f} ms").format(high=m['high']*1000))
        print(_("  Low pulse      : {low:.3f} ms").format(low=m['low']*1000))
        print(_("  Duty           : {duty:.1f} %   ({cycles} cycles averaged)").format(
            duty=m['duty'], cycles=m['cycles']))
    else:
        print(_("  Signal insufficient"))


def run():
    """Offline tools submenu: choice 0 returns to the main menu."""
    while True:
        print()
        print(_("===== Offline tools ====="))
        print(_("  [1] Full offline self-test report (no hardware, zero flashing, for acceptance)"))
        print(_("  [2] PPM multi-channel extension check"))
        print(_("  [3] Export all events to CSV"))
        print(_("  [4] Pulse statistics and glitch detection"))
        print(_("  [5] Dual-waveform diff"))
        print(_("  [6] HTML waveform browser export"))
        print(_("  [7] File analysis (UART decode + measurement)"))
        print(_("  [0] Back to main menu"))
        sel = input(_("Select: ")).strip()
        if sel == "1":
            report_all()
        elif sel == "2":
            check_ppm()
        elif sel == "3":
            export_csv()
        elif sel == "4":
            pulse_stats()
        elif sel == "5":
            diff_flow()
        elif sel == "6":
            html_export()
        elif sel == "7":
            file_analysis()
        elif sel == "0":
            return
        else:
            print(_("Invalid choice"))
            continue
        console.pause()
