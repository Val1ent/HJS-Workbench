# -*- coding: utf-8 -*-
"""Main menu loop and navigation for the unified CLI."""
from . import console  # noqa: F401  (helpers are used by every sub-flow)
from . import capture_flow, live_analyzer, live_measure
from . import offline_flow, protocol_flow, signal_flow
from .version import __version__

MENU = [
    "1. Capture to file",
    "2. Live analyzer",
    "3. Live measurement",
    "4. Protocol decoder",
    "5. Signal generator",
    "6. Offline tools",
    "0. Quit",
]


def show_menu():
    print("=" * 64)
    print(f"口袋数字调试助手 · 统一命令行 v{__version__}")
    print("=" * 64)
    for line in MENU:
        print(line)


def main():
    """主菜单循环：各子流程结束后返回本菜单，只有选择 0 才退出。"""
    while True:
        show_menu()
        sel = input("选择: ").strip()
        if sel == "1":
            capture_flow.run()
        elif sel == "2":
            live_analyzer.run()
        elif sel == "3":
            live_measure.run()
        elif sel == "4":
            protocol_flow.run()
        elif sel == "5":
            signal_flow.run()
        elif sel == "6":
            offline_flow.run()
        elif sel == "0":
            print("已退出。")
            return
        else:
            print("无效选择")
