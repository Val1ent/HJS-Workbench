# -*- coding: utf-8 -*-
"""
Quick start guide console page: the same five-step guide as the GUI
onboarding wizard, re-openable at any time from the main menu.
"""
from core.guide import GUIDE_STEPS
from core.i18n import _
from . import console


def run():
    print("=" * 64)
    print(_("Quick Start Guide"))
    print("=" * 64)
    for number, (title, lines) in enumerate(GUIDE_STEPS, 1):
        print(_("Step {number}: {title}").format(
            number=number, title=_(title)))
        for line in lines:
            print("  " + _(line))
        print()
    console.pause()
