# -*- coding: utf-8 -*-
"""Entry point: `python -m gui` from the repository root.

Also works when run directly as `python gui/__main__.py`; in that case the
repository root (the parent directory of gui/) is put on sys.path first so
that the gui package and the top-level `core` package both resolve.
"""
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from gui.app import main
else:
    from .app import main

if __name__ == "__main__":
    main()
