# ============================================================
#  fin — Selachii Adoption Script
#  Selachii Project © 2026 — GPL v3
#  scripts/adopt_lfs.py — registers LFS base into LocalDB
# ============================================================
#
#  Scans the actual filesystem to verify each protected package
#  has real binaries/libraries on disk before registering it.
#  Packages with no files found are skipped with a warning.
# ============================================================

import argparse
import os
import sys
from pathlib import Path

sys.path.append(os.getcwd())

from fin.config import get_config
from fin.db.local_db import LocalDB
from fin.db.models import Package


# ── Package definitions ───────────────────────────────────────
# Each entry: package_name → { provides, verify_any }
# verify_any: list of paths — at least one must exist on disk
# for the package to be considered installed.

LFS_PACKAGES = {
    "bash": {
        "provides": ["sh"],
        "verify_any": ["/bin/bash", "/usr/bin/bash"],
    },
    "glibc": {
        "provides": ["libc.so", "libm.so", "libpthread.so", "ld-linux-x86-64.so.2"],
        "verify_any": ["/lib/libc.so.6", "/usr/lib/libc.so.6", "/lib64/libc.so.6"],
    },
    "gcc": {
        "provides": ["cc", "gcc"],
        "verify_any": ["/usr/bin/gcc"],
    },
    "binutils": {
        "provides": ["ld", "as"],
        "verify_any": ["/usr/bin/ld", "/usr/bin/as"],
    },
    "linux-api-headers": {
        "provides": [],
        "verify_any": ["/usr/include/linux/version.h", "/usr/include/linux/types.h"],
    },
    "zlib": {
        "provides": ["libz.so"],
        "verify_any": ["/usr/lib/libz.so", "/usr/lib/libz.so.1", "/lib/libz.so.1"],
    },
    "bzip2": {
        "provides": ["libbz2.so"],
        "verify_any": ["/usr/bin/bzip2", "/usr/lib/libbz2.so.1"],
    },
    "xz": {
        "provides": [],
        "verify_any": ["/usr/bin/xz"],
    },
    "zstd": {
        "provides": ["libzstd.so"],
        "verify_any": ["/usr/bin/zstd", "/usr/lib/libzstd.so.1"],
    },
    "file": {
        "provides": ["libmagic.so"],
        "verify_any": ["/usr/bin/file"],
    },
    "readline": {
        "provides": ["libreadline.so"],
        "verify_any": ["/usr/lib/libreadline.so.8", "/usr/lib/libreadline.so"],
    },
    "m4": {
        "provides": [],
        "verify_any": ["/usr/bin/m4"],
    },
    "bc": {
        "provides": [],
        "verify_any": ["/usr/bin/bc"],
    },
    "flex": {
        "provides": [],
        "verify_any": ["/usr/bin/flex"],
    },
    "tcl": {
        "provides": [],
        "verify_any": ["/usr/bin/tclsh"],
    },
    "expect": {
        "provides": [],
        "verify_any": ["/usr/bin/expect"],
    },
    "dejagnu": {
        "provides": [],
        "verify_any": ["/usr/bin/runtest"],
    },
    "pkgconf": {
        "provides": ["pkg-config"],
        "verify_any": ["/usr/bin/pkgconf", "/usr/bin/pkg-config"],
    },
    "sed": {
        "provides": [],
        "verify_any": ["/usr/bin/sed", "/bin/sed"],
    },
    "psmisc": {
        "provides": [],
        "verify_any": ["/usr/bin/killall"],
    },
    "gettext": {
        "provides": [],
        "verify_any": ["/usr/bin/gettext"],
    },
    "bison": {
        "provides": [],
        "verify_any": ["/usr/bin/bison"],
    },
    "grep": {
        "provides": [],
        "verify_any": ["/usr/bin/grep", "/bin/grep"],
    },
    "gzip": {
        "provides": [],
        "verify_any": ["/usr/bin/gzip", "/bin/gzip"],
    },
    "iproute2": {
        "provides": [],
        "verify_any": ["/usr/sbin/ip", "/sbin/ip"],
    },
    "kbd": {
        "provides": [],
        "verify_any": ["/usr/bin/loadkeys"],
    },
    "libpipeline": {
        "provides": [],
        "verify_any": ["/usr/lib/libpipeline.so.1"],
    },
    "make": {
        "provides": [],
        "verify_any": ["/usr/bin/make"],
    },
    "patch": {
        "provides": [],
        "verify_any": ["/usr/bin/patch"],
    },
    "tar": {
        "provides": [],
        "verify_any": ["/usr/bin/tar", "/bin/tar"],
    },
    "texinfo": {
        "provides": [],
        "verify_any": ["/usr/bin/makeinfo"],
    },
    "vim": {
        "provides": [],
        "verify_any": ["/usr/bin/vim"],
    },
    "util-linux": {
        "provides": ["libuuid.so", "libblkid.so", "libmount.so", "uuid"],
        "verify_any": ["/usr/bin/mount", "/bin/mount"],
    },
    "man-db": {
        "provides": [],
        "verify_any": ["/usr/bin/man"],
    },
    "openssl": {
        "provides": ["libssl.so", "libcrypto.so"],
        "verify_any": ["/usr/bin/openssl"],
    },
    "curl": {
        "provides": ["libcurl.so"],
        "verify_any": ["/usr/bin/curl"],
    },
    "gawk": {
        "provides": ["awk"],
        "verify_any": ["/usr/bin/gawk", "/usr/bin/awk"],
    },
    "coreutils": {
        "provides": [],
        "verify_any": ["/usr/bin/ls", "/bin/ls"],
    },
    "diffutils": {
        "provides": [],
        "verify_any": ["/usr/bin/diff"],
    },
    "findutils": {
        "provides": [],
        "verify_any": ["/usr/bin/find"],
    },
    "gdbm": {
        "provides": ["libgdbm.so"],
        "verify_any": ["/usr/lib/libgdbm.so.6", "/usr/lib/libgdbm.so"],
    },
    "gmp": {
        "provides": ["libgmp.so"],
        "verify_any": ["/usr/lib/libgmp.so.10", "/usr/lib/libgmp.so"],
    },
    "mpfr": {
        "provides": ["libmpfr.so"],
        "verify_any": ["/usr/lib/libmpfr.so.6", "/usr/lib/libmpfr.so"],
    },
    "mpc": {
        "provides": ["libmpc.so"],
        "verify_any": ["/usr/lib/libmpc.so.3", "/usr/lib/libmpc.so"],
    },
    "attr": {
        "provides": ["libattr.so"],
        "verify_any": ["/usr/lib/libattr.so.1"],
    },
    "acl": {
        "provides": ["libacl.so"],
        "verify_any": ["/usr/lib/libacl.so.1"],
    },
    "shadow": {
        "provides": [],
        "verify_any": ["/usr/bin/passwd", "/usr/sbin/useradd"],
    },
    "openrc": {
        "provides": [],
        "verify_any": ["/sbin/openrc", "/usr/sbin/openrc", "/sbin/rc-service"],
    },
}


def verify_on_disk(pkg_name: str, verify_any: list[str], root: str = "/") -> tuple[bool, list[str]]:
    """
    Check if at least one of the expected paths exists on disk.
    Returns (found: bool, found_paths: list[str])
    """
    found = []
    for rel_path in verify_any:
        full = Path(root) / rel_path.lstrip("/")
        if full.exists():
            found.append(str(full))
    return len(found) > 0, found


def collect_installed_files(pkg_name: str, verify_any: list[str], root: str = "/") -> list[str]:
    """
    Collect all verify_any paths that actually exist on disk.
    Used to populate the LocalDB files list for adopted packages.
    """
    found = []
    for rel_path in verify_any:
        full = Path(root) / rel_path.lstrip("/")
        if full.exists():
            found.append(str(full))
    return found


def adopt(dry_run: bool = False, verbose: bool = False, root: str = "/"):
    config = get_config()
    db     = LocalDB()

    print(f"   :: Verifying and adopting LFS base packages (root={root})...")
    print()

    adopted  = 0
    skipped  = 0
    missing  = 0

    for pkg_name, info in LFS_PACKAGES.items():
        verify_any = info.get("verify_any", [])
        provides   = info.get("provides", [])

        # Already in DB — skip
        if db.has(pkg_name):
            if verbose:
                print(f"      = {pkg_name}: already registered, skipping")
            skipped += 1
            continue

        # Verify on disk
        found, found_paths = verify_on_disk(pkg_name, verify_any, root)

        if not found:
            print(f"      ✗ {pkg_name}: not found on disk — skipping")
            print(f"        (checked: {', '.join(verify_any)})")
            missing += 1
            continue

        if verbose:
            print(f"      ✓ {pkg_name}: found at {found_paths[0]}")
        else:
            print(f"      + Adopting {pkg_name}")

        if not dry_run:
            files = collect_installed_files(pkg_name, verify_any, root)
            db.register(
                Package(
                    name=pkg_name,
                    version="LFS-BASE",
                    desc="Core LFS system package (managed by original build)",
                    url="https://www.linuxfromscratch.org",
                    provides=provides,
                    origin="explicit",
                ),
                files=files,
                explicit=True,
            )
        adopted += 1

    print()
    print(f"   ✓ Adoption complete.")
    print(f"     Adopted : {adopted}")
    print(f"     Skipped : {skipped} (already in DB)")
    print(f"     Missing : {missing} (not found on disk — will be installable via fin)")

    if dry_run:
        print("   ✓ Dry-run mode: LocalDB was not modified.")
    if missing > 0:
        print(f"\n   ℹ  Missing packages are not errors — they simply weren't")
        print(f"      built as part of your LFS base and can be installed with fin.")


def main():
    parser = argparse.ArgumentParser(
        description="Adopt core LFS packages into fin LocalDB"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be adopted without writing to DB"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show each package's verification path"
    )
    parser.add_argument(
        "--root", default="/",
        help="Alternate install root (default: /)"
    )
    args = parser.parse_args()
    adopt(dry_run=args.dry_run, verbose=args.verbose, root=args.root)


if __name__ == "__main__":
    main()
