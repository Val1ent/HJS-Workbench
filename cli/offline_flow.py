# -*- coding: utf-8 -*-
"""
离线工具子菜单：自检报告、PPM 验证、CSV 导出、脉冲统计、双波形对比、
HTML 波形导出与文件分析（对应 proto_lab / proto_stats / proto_diff /
proto_browser 的离线能力）。
"""
import csv
import json
import os
import statistics

import core
from core.decoders.servo import decode_servo
from core.model import channel_bits
from core.segments import build_wave, pulse_widths
from . import console

SAMPLE_RATE = 10000

# ---- 验收规则：自测事件里必须出现的（类型, 关键内容） ----
REQUIRED = {
    "nec":        [("LEADER", None), ("NEC", "地址=0x00 命令=0x45"), ("REPEAT", None)],
    "servo":      [("SERVO", "角度=0.0°"), ("SERVO", "角度=90.0°"),
                   ("SERVO", "角度=180.0°")],
    "i2c":        [("START", None), ("ADDR", "0x48 W ACK"),
                   ("DATA", "0x55 ACK"), ("STOP", None)],
    "spi":        [("CS_LOW", None), ("SPI", "MOSI=0x3C MISO=0x11"),
                   ("SPI", "MOSI=0xA5 MISO=0x22"), ("CS_HIGH", None)],
    "stepper":    [("STEP", "第1步"), ("STEP_SUM", "共40步"), ("STEP_SUM", "累计=+20")],
    "encoder":    [("ENCODER", None), ("ZERO", None)],
    "rc5":        [("RC5", "地址=5 命令=33")],
    "ultrasonic": [("TRIG", None), ("DISTANCE", "距离≈17.0cm"),
                   ("DISTANCE", "距离≈25.5cm")],
    "fan":        [("FAN", None), ("FAN_SUM", "平均=3000RPM")],
}
FORBIDDEN = {
    "nec": [("NEC_ERR", None)],        # NEC 校验错误一条都不能有
}


def check_deck(name, events):
    """按 REQUIRED/FORBIDDEN 核对事件，返回 (ok, 问题列表)。"""
    problems = []
    for typ, sub in REQUIRED.get(name, []):
        hits = [e for e in events if e["type"] == typ
                and (sub is None or sub in e["text"])]
        if not hits:
            problems.append(f"缺 {typ} {sub or ''}".strip())
    for typ, sub in FORBIDDEN.get(name, []):
        hits = [e for e in events if e["type"] == typ
                and (sub is None or sub in e["text"])]
        if hits:
            problems.append(f"出现禁止项 {typ} x{len(hits)}")
    return (len(problems) == 0), problems


def report_all():
    """跑全部 9 个解码器自测并核对预期，打印验收报告。返回是否全部通过。"""
    print("=" * 64)
    print("全量协议自检报告（纯离线 · 零烧录 · 可重复验收）")
    print("=" * 64)
    passed = 0
    total = 0
    for name, deck in core.DECKS.items():
        total += 1
        try:
            samples = deck["make"](SAMPLE_RATE)
            events = deck["decode"](samples, SAMPLE_RATE)
            ok, problems = check_deck(name, events)
        except Exception as exc:
            ok, problems, events = False, [f"异常: {exc}"], []
        if ok:
            passed += 1
        print(f"\n[{'PASS' if ok else 'FAIL'}] {name:<10} {deck['desc']}"
              f"  事件 {len(events)} 条")
        for p in problems:
            print("        问题: " + p)
        for e in events[:5]:
            print(f"        {e['t']*1000:8.3f}ms  {e['type']:<10} {e['text']}")
        if len(events) > 5:
            print(f"        ... 其余 {len(events)-5} 条略")
    print("\n" + "=" * 64)
    print(f"验收结果: {passed}/{total} 通过" + ("  [OK]" if passed == total else "  [FAIL]"))
    return passed == total


def make_ppm_test(rate):
    """PPM 演示：8 通道，间隔依次 1000~1800us，帧同步 >4000us。"""
    n = int(0.06 * rate)
    pulses = []
    t = 0.003
    for us in (1000, 1200, 1400, 1600, 1800, 1500, 1300, 1100):
        pulses.append((t, 1, 0.0004))       # 400us 通道脉冲
        t += us / 1e6
    pulses.append((t, 1, 0.0004))           # 帧尾短脉冲，凑出第 8 个通道值
    return build_wave(0, pulses, rate, n, idle=0)


def check_ppm():
    """验证 decode_servo 的 PPM 分支：8 通道帧且不误报 SERVO。"""
    samples = make_ppm_test(SAMPLE_RATE)
    events = decode_servo(samples, SAMPLE_RATE, ch=0)
    ppm = [e for e in events if e["type"] == "PPM"]
    servos = [e for e in events if e["type"] == "SERVO"]
    ok = len(ppm) == 1 and "8通道" in ppm[0]["text"] and not servos
    print("=" * 64)
    print(f"[{'PASS' if ok else 'FAIL'}] PPM 多通道扩展验证")
    for e in events:
        print(f"  {e['t']*1000:9.3f} ms  D{e['ch']}  {e['type']:<10} {e['text']}")
    print("说明: 帧内 8 个通道间隔被识别为 PPM，且未误报成 SERVO（间隔≠20ms）。")
    return ok


def export_csv():
    """把全部解码器自测事件导出为 CSV（utf-8-sig，Excel 可直接打开）。"""
    path = os.path.join(os.getcwd(), "proto_lab_events.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["解码器", "类型", "时间ms", "通道", "内容"])
        for name in core.DECKS:
            samples = core.DECKS[name]["make"](SAMPLE_RATE)
            for e in core.DECKS[name]["decode"](samples, SAMPLE_RATE):
                w.writerow([name, e["type"], f"{e['t']*1000:.3f}",
                            f"D{e['ch']}", e["text"]])
    print("已导出:", path)


# ----------------------------------------------------------------------
# 脉冲统计与毛刺检测（对应 proto_stats.py）
# ----------------------------------------------------------------------
BINS_MS = [(0, 0.1), (0.1, 0.2), (0.2, 0.5), (0.5, 1), (1, 2), (2, 5),
           (5, 10), (10, 20), (20, 50), (50, 1e9)]
BIN_LABEL = ["<0.1ms", "0.1~0.2", "0.2~0.5", "0.5~1", "1~2", "2~5",
             "5~10", "10~20", "20~50", ">=50"]


def load(path, rate):
    """读取 .sr 或 .bin → (rate, samples)。"""
    if path.lower().endswith(".sr"):
        r, s = core.read_sr(path)
        if rate:
            r = rate
        return r, s
    r = rate or 10000
    return r, core.read_bin(path, r)[1]


def analyze(bits, rate, glitch_s):
    """单通道体检，返回指标 dict。"""
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
    # 宽度统计：剔除首尾两个可能被截断的段
    body = segs[1:-1] if len(segs) >= 3 else segs
    widths = [w for (_, _, w) in body]
    stats = None
    if widths:
        stats = {"min": min(widths), "max": max(widths),
                 "mean": statistics.mean(widths),
                 "median": statistics.median(widths), "count": len(widths)}
    # 直方图
    hist = [0] * len(BINS_MS)
    for w in widths:
        for bi, (lo, hi) in enumerate(BINS_MS):
            if lo * 1e-3 <= w < hi * 1e-3:
                hist[bi] += 1
                break
    # 毛刺：比阈值窄的脉冲
    glitches = [(s, lvl, w) for (s, lvl, w) in body if w < glitch_s]
    return {"edges": edges, "freq": freq, "duty": duty, "stats": stats,
            "hist": hist, "glitches": glitches}


def report_channel(ch, res, rate, glitch_s):
    print(f"\n---- D{ch} ----")
    if res["edges"] == 0:
        print("  静默：整段无跳变（疑似悬空/常电平/未接线）")
        return
    line = f"  翻转 {res['edges']} 次"
    if res["freq"]:
        line += f" | 频率≈{res['freq']:.1f} Hz"
    if res["duty"] is not None:
        line += f" | 占空比≈{res['duty']:.1f}%"
    print(line)
    s = res["stats"]
    if s:
        print(f"  脉冲宽度: 最小 {s['min']*1e6:.0f}us | 中位 {s['median']*1e6:.0f}us | "
              f"平均 {s['mean']*1e6:.0f}us | 最大 {s['max']*1e6:.0f}us （{s['count']} 段）")
    mx = max(res["hist"]) or 1
    print("  宽度直方图:")
    for bi in range(len(BINS_MS)):
        c = res["hist"][bi]
        if c:
            print(f"    {BIN_LABEL[bi]:>8} {c:4d}  {'█' * max(1, int(c / mx * 36))}")
    if res["glitches"]:
        print(f"  [!] 毛刺（<{glitch_s*1e6:.0f}us）{len(res['glitches'])} 处:")
        for (s_i, lvl, w) in res["glitches"][:12]:
            print(f"    {s_i / rate * 1000:8.3f} ms  宽 {w*1e6:.0f}us  电平={lvl}")
        if len(res["glitches"]) > 12:
            print(f"    ... 其余 {len(res['glitches'])-12} 处见 CSV")
    else:
        print(f"  毛刺: 无（阈值 {glitch_s*1e6:.0f}us）")


def pulse_stats():
    """交互版脉冲统计与毛刺检测（对应 proto_stats.py 的 main）。"""
    path = input("采集文件路径(.sr/.bin)，回车用解码器演示波形: ").strip()
    if path:
        raw_rate = console.read_int("采样率(回车默认10000): ", 10000)
        rate = raw_rate if raw_rate is not None else 10000
        r, samples = load(path, rate)
        rate = r
        src = path
    else:
        deck_name = console.choose_decoder()
        if deck_name is None:
            return
        rate = console.read_int("采样率(回车默认10000): ", 10000)
        if rate is None:
            rate = 10000
        samples = core.DECKS[deck_name]["make"](rate)
        src = f"演示波形 {deck_name}（{core.DECKS[deck_name]['desc']}）"

    raw = input("毛刺阈值us(回车默认200): ").strip()
    try:
        glitch_us = float(raw) if raw else 200.0
    except ValueError:
        glitch_us = 200.0
    raw = input("通道列表(逗号分隔, 回车默认全部): ").strip()
    if raw:
        try:
            chs = [int(x) for x in raw.split(",")]
        except ValueError:
            print("通道列表无效，使用全部通道")
            chs = list(range(8))
    else:
        chs = list(range(8))
    out = input("CSV 输出路径(回车默认 proto_stats_报告.csv): ").strip() \
        or os.path.join(os.getcwd(), "proto_stats_报告.csv")

    glitch_s = glitch_us * 1e-6
    print("=" * 64)
    print(f"脉冲统计与毛刺检测  |  {src}")
    print(f"采样率 {rate} Hz · {len(samples)} 点"
          f"（{len(samples)/rate*1000:.1f} ms） · 毛刺阈值 {glitch_us:.0f}us")
    results = {}
    for ch in chs:
        res = analyze(channel_bits(samples, ch), rate, glitch_s)
        results[ch] = res
        report_channel(ch, res, rate, glitch_s)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["通道", "类别", "时间ms", "数值", "说明"])
        for ch in chs:
            r = results[ch]
            s = r["stats"]
            w.writerow([f"D{ch}", "SUMMARY", "", f"{r['edges']}", "翻转次数"])
            if r["freq"]:
                w.writerow([f"D{ch}", "SUMMARY", "", f"{r['freq']:.2f}", "平均频率Hz"])
            if r["duty"] is not None:
                w.writerow([f"D{ch}", "SUMMARY", "", f"{r['duty']:.2f}", "平均占空比%"])
            if s:
                w.writerow([f"D{ch}", "SUMMARY", "", f"{s['min']*1e6:.0f}", "最小脉宽us"])
                w.writerow([f"D{ch}", "SUMMARY", "", f"{s['max']*1e6:.0f}", "最大脉宽us"])
            for (s_i, lvl, wd) in r["glitches"]:
                w.writerow([f"D{ch}", "GLITCH", f"{s_i/rate*1000:.3f}",
                            f"{wd*1e6:.0f}us", f"电平={lvl}"])
    print(f"\n报告已导出: {out}")


# ----------------------------------------------------------------------
# 双波形对比（对应 proto_diff.py）
# ----------------------------------------------------------------------
def diff_segments(a_bits, b_bits):
    """返回差异区间 [(start, end_exclusive), ...]。"""
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
    print("双波形对比报告（A=基准 · B=待测）")
    print(f"A = {path_a}  ({len(A)} 点)")
    print(f"B = {path_b}  ({len(B)} 点)")
    if len(A) != len(B):
        print(f"长度不同：仅对比重叠部分 {n} 点")
    print("=" * 64)

    first_global = None
    per = []
    for ch in range(8):
        ab = channel_bits(A, ch)[:n]
        bb = channel_bits(B, ch)[:n]
        segs = diff_segments(ab, bb)
        cnt = sum(e - s for (s, e) in segs)
        if cnt and (first_global is None or segs[0][0] < first_global):
            first_global = segs[0][0]
        per.append((ch, cnt, segs))

    total = sum(c for (_, c, _) in per)
    sim = 100.0 * (1.0 - total / (n * 8.0)) if n else 100.0
    print(f"\n总体相似度: {sim:.4f}%   差异采样点: {total} / {n * 8}")
    if first_global is not None:
        print(f"首个差异: {first_global * dt * 1000:.3f} ms (第 {first_global} 点)")
    print("\n通道     差异点     占比     差异区间数")
    for (ch, cnt, segs) in per:
        print(f"  D{ch}    {cnt:7d}   {cnt / n * 100:6.2f}%    {len(segs):6d}")

    # ASCII 对照带：围绕首个差异
    if first_global is not None:
        w = 80
        lo = max(0, first_global - w // 2)
        hi = min(n, lo + w)
        print(f"\n-- 局部对照（第 {lo}~{hi} 点，█=高 _=低 ^=差异）--")
        for ch in range(8):
            ab = channel_bits(A, ch)[:n]
            bb = channel_bits(B, ch)[:n]
            la = "".join("█" if ab[i] else "_" for i in range(lo, hi))
            lb = "".join("█" if bb[i] else "_" for i in range(lo, hi))
            mark = "".join("^" if ab[i] != bb[i] else " " for i in range(lo, hi))
            if mark.strip():
                print(f"D{ch} A {la}\n    B {lb}\n      {mark}")

    # CSV 差异清单
    out = csv_path or os.path.join(os.getcwd(), "proto_diff_报告.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        wcsv = csv.writer(f)
        wcsv.writerow(["通道", "起始ms", "结束ms", "差异点数"])
        for (ch, cnt, segs) in per:
            for (s, e) in segs:
                wcsv.writerow([f"D{ch}", f"{s * dt * 1000:.3f}",
                               f"{e * dt * 1000:.3f}", e - s])
    print(f"\n差异区间清单已导出: {out}")
    return sim


def diff_flow():
    """交互版双波形对比（对应 proto_diff.py 的 main）。"""
    path_a = input("基准波形 A 路径(.sr/.bin): ").strip()
    if not path_a:
        return
    path_b = input("待测波形 B 路径(.sr/.bin): ").strip()
    if not path_b:
        return
    raw = input("采样率(仅 .bin, 回车自动): ").strip()
    rate = None
    if raw:
        try:
            rate = int(raw)
        except ValueError:
            rate = None
    csv_path = input("CSV 输出路径(回车默认 proto_diff_报告.csv): ").strip() or None
    run_diff(path_a, path_b, rate, csv_path)


# ----------------------------------------------------------------------
# 交互式波形浏览器导出（对应 proto_browser.py）
# ----------------------------------------------------------------------
TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
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
<div id="bar"><b>@@TITLE@@</b> ｜ 滚轮缩放 · 按住拖动平移 · 单击=A光标 · Shift+单击=B光标</div>
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
  var msg='视图 '+v0+'~'+v1+' / '+SAMPLES.length+' 点 · '+spp.toFixed(2)+' 点/像素';
  if(curA!==null){msg+='  |  A@'+((curA/RATE)*1000).toFixed(3)+'ms';}
  if(curB!==null){msg+='  |  B@'+((curB/RATE)*1000).toFixed(3)+'ms';}
  if(curA!==null&&curB!==null){msg+='  |  Δt='+(Math.abs(curB-curA)/RATE*1000).toFixed(3)+'ms';}
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
  if(!EVENTS.length){box.innerHTML='<div style="color:#5b6f83;padding:4px 0">无解码事件（未叠加解码器）</div>';return;}
  var n=Math.min(EVENTS.length,300), html='<div style="padding:4px 0;color:#8fb0cc">解码事件（前'+n+'条，点击跳转）：</div>';
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
    """生成单文件 HTML。"""
    # 每通道统计
    stats_rows = []
    for ch in range(8):
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
    stats_html = ("<table><tr><th>通道</th><th>平均频率</th><th>平均占空比</th>"
                  "<th>翻转次数</th></tr>" + "".join(stats_rows) + "</table>")

    title_safe = title.replace("&", "&amp;").replace("<", "&lt;")
    info = (f"采样率 {rate} Hz · {len(samples)} 点 · "
            f"时长 {len(samples) / rate * 1000:.1f} ms · 事件 {len(events)} 条")
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
    """交互版单文件 HTML 波形导出（对应 proto_browser.py 的 main）。"""
    path = input("采集文件路径(.sr/.bin)，回车用解码器演示波形: ").strip()
    if path:
        r, samples = load(path, None)
        rate = r
        dec_name = input("叠加解码器名(回车跳过): ").strip()
        events = []
        if dec_name:
            if dec_name not in core.DECKS:
                print("未知解码器:", dec_name, "可选:", list(core.DECKS))
                return
            try:
                events = core.DECKS[dec_name]["decode"](samples, rate)
            except Exception as exc:
                print("解码失败(忽略):", exc)
        title = f"{os.path.basename(path)} · {rate} Hz"
    else:
        deck_name = console.choose_decoder()
        if deck_name is None:
            return
        rate = console.read_int("采样率(回车默认10000): ", 10000)
        if rate is None:
            rate = 10000
        samples = core.DECKS[deck_name]["make"](rate)
        events = core.DECKS[deck_name]["decode"](samples, rate)
        title = f"{deck_name} · {core.DECKS[deck_name]['desc']} 演示波形"

    out = input("输出文件(回车默认 proto_wave.html): ").strip() \
        or os.path.join(os.getcwd(), "proto_wave.html")
    html = build_html(title, rate, samples, events)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成: {out}  ({os.path.getsize(out)} 字节)")
    ans = input("生成后自动打开浏览器?(回车=是, n=否): ").strip().lower()
    if ans != "n":
        try:
            os.startfile(out)
        except Exception:
            print("（未能自动打开，请手动双击该文件）")


# ----------------------------------------------------------------------
# 文件分析：UART 解码 + D0 测量
# ----------------------------------------------------------------------
def file_analysis():
    """打开一个采集文件，跑 UART 文本解码与 D0 测量。"""
    path = input("采集文件路径(.sr/.bin): ").strip()
    if not path:
        return
    try:
        rate, samples = core.acquire_file(path)
    except Exception as exc:
        print("读取失败:", exc)
        return
    print(f"已打开: {path}")
    print(f"采样率 {rate} Hz · {len(samples)} 点 · 时长 {len(samples)/rate*1000:.1f} ms")

    bits = channel_bits(samples, 0)
    frames = core.scan_frames(bits)
    text = "".join(c for _, c in frames)
    print("\n-- UART 解码 (D0, 1000bps 8N1) --")
    print("  接收到:", repr(text) if text else "(未解码出完整帧)")

    m = core.measure(bits)
    print("\n-- D0 测量 --")
    if m:
        print(f"  频率      : {m['freq']:.1f} Hz")
        print(f"  周期      : {m['period']*1000:.3f} ms  "
              f"(min {m['pmin']*1000:.3f} / max {m['pmax']*1000:.3f})")
        print(f"  高电平脉宽: {m['high']*1000:.3f} ms")
        print(f"  低电平脉宽: {m['low']*1000:.3f} ms")
        print(f"  占空比    : {m['duty']:.1f} %   ({m['cycles']} 周期平均)")
    else:
        print("  信号不足")


def run():
    """离线工具子菜单：选择 0 返回主菜单。"""
    while True:
        print()
        print("===== 离线工具 =====")
        print("  [1] 全量离线自检报告（无需硬件 · 零烧录 · 验收用）")
        print("  [2] PPM 多通道扩展验证")
        print("  [3] 导出全部事件 CSV")
        print("  [4] 脉冲统计与毛刺检测")
        print("  [5] 双波形对比")
        print("  [6] HTML 波形浏览器导出")
        print("  [7] 文件分析（UART 解码 + 测量）")
        print("  [0] 返回主菜单")
        sel = input("选择: ").strip()
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
            print("无效选择")
            continue
        console.pause()
