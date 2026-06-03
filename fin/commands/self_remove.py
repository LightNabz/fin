# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  fin/commands/self_remove.py — Uninstall fin itself
# ============================================================

import os
import sys
import shutil

from ..ui.output import print_section, print_success, print_error, print_info, print_warning
from ..ui.prompt import confirm

# Everything sven owns on the filesystem
_SVEN_PATHS = [
    "/usr/bin/fin",
    "/etc/fin",
    "/var/lib/fin",
    "/var/cache/fin",
    "/var/log/fin",
    "/tmp/fin",
]


def run() -> None:
    print_section("fin Self-Remove")

    if os.geteuid() != 0:
        print_error("self-remove must be run as root.")
        print("   Try: sudo fin self-remove")
        sys.exit(1)

    print_warning("This will permanently delete fin and all its data:")
    print()
    for p in _SVEN_PATHS:
        exists = os.path.exists(p)
        marker = "  ✗" if exists else "  ·"
        label = p if exists else f"{p}  (not present)"
        print(f"   {marker}  {label}")
    print()

    if not confirm("Are you sure you want to remove fin completely?", default=False):
        print_info("Aborted — fin is still installed.")
        sys.exit(0)

    errors = []
    for path in _SVEN_PATHS:
        if not os.path.exists(path):
            continue
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print_info(f"Removed: {path}")
        except Exception as e:
            errors.append(f"{path}: {e}")

    if errors:
        print()
        print_error("Some paths could not be removed:")
        for err in errors:
            print(f"   · {err}")
        sys.exit(1)

    print()
    print_success("fin has been completely removed from this system.")
    print("   Goodbye. You can reinstall anytime from:")
    print("   https://github.com/YOUR_USERNAME/fin")
    # No sys.exit — the process ends naturally after this print.
    # (The binary may already be gone, but we're still running in-memory.)
