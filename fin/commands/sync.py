# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  fin/commands/sync.py
# ============================================================
from ..db.sync_db import SyncDB
from ..ui import print_banner, print_section, print_success

def run(**kwargs):
    print_banner()
    print_section("Synchronizing databases...")

    sync = SyncDB()
    sync.sync()

    print_success("Databases synchronized successfully.")
