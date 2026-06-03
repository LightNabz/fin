#!/usr/bin/env python3
# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  run_fin.py — direct entry point (no install required)
# ============================================================
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fin.__main__ import main

if __name__ == "__main__":
    main()
