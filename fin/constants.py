# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  constants.py — global constants, paths, URLs
# ============================================================

import os
import sys

# ── Dynamic Root parsing ─────────────────────────────────────
_ROOT = ""
try:
    if "--root" in sys.argv:
        _ROOT = sys.argv[sys.argv.index("--root") + 1].rstrip("/")
    elif "-r" in sys.argv:
        _ROOT = sys.argv[sys.argv.index("-r") + 1].rstrip("/")
except Exception:
    pass

# ── Version ──────────────────────────────────────────────────
VERSION       = "1.0.0"
CODENAME      = "Dorsal"

# ── Identity ─────────────────────────────────────────────────
APP_NAME      = "fin"
BRAND         = "Selachii Project"
OS_NAME       = "Selachii"
GITHUB        = "https://github.com/LightNabz/fin"

# ── Install Root (overridable via --root flag) ───────────────
DEFAULT_ROOT  = _ROOT or "/"

# ── fin DB Paths ─────────────────────────────────────────────
DB_BASE       = f"{_ROOT}/var/lib/fin"
DB_INSTALLED  = f"{DB_BASE}/installed"
DB_SYNC       = f"{DB_BASE}/sync"
DB_AUR_CACHE  = f"{DB_BASE}/aur_cache"
DB_SNAPSHOTS  = f"{DB_BASE}/snapshots"
DB_LOCK       = f"{DB_BASE}/lock"

# ── Cache ────────────────────────────────────────────────────
CACHE_BASE    = f"{_ROOT}/var/cache/fin"
CACHE_PKGS    = f"{CACHE_BASE}/pkgs"
CACHE_AUR     = f"{CACHE_BASE}/aur"

# ── Logging ──────────────────────────────────────────────────
LOG_DIR       = f"{_ROOT}/var/log/fin"
LOG_MAIN      = f"{LOG_DIR}/fin.log"
LOG_HOOKS     = f"{LOG_DIR}/hooks.log"

# ── Config ───────────────────────────────────────────────────
CONFIG_DIR    = f"{_ROOT}/etc/fin"
CONFIG_FILE   = f"{CONFIG_DIR}/fin.conf"
INITSCRIPTS   = f"{CONFIG_DIR}/initscripts"

# ── Temp / Build ─────────────────────────────────────────────
TMP_BASE      = f"{_ROOT}/tmp/fin"
TMP_AUR       = f"{TMP_BASE}/aur"
TMP_BUILD     = f"{TMP_BASE}/build"

# ── Artix Repos ──────────────────────────────────────────────
# Official Artix repos — init-agnostic + per-init variants
ARCH_REPOS    = ["world", "world-openrc", "world-runit", "world-s6", "system", "lib32"]
ARCH_ARCH     = "x86_64"

# ── Default Mirror ───────────────────────────────────────────
DEFAULT_MIRROR         = "https://mirror.pascalpuffke.de/artix-linux"
ARTIX_MIRROR_LIST_URL  = "https://gitea.artixlinux.org/packagesA/artix-mirrorlist/raw/branch/master/mirrorlist"

# ── Mirror DB URL Template ───────────────────────────────────
# Usage: MIRROR_DB_URL.format(mirror=..., repo=..., arch=...)
MIRROR_DB_URL  = "{mirror}/{repo}/os/{arch}/{repo}.db"
MIRROR_PKG_URL = "{mirror}/{repo}/os/{arch}/{filename}"

# ── AUR ──────────────────────────────────────────────────────
# fin uses the Artix AUR (gitea) for init-aware packages,
# falling back to the Arch AUR for everything else.
ARTIX_AUR_URL  = "https://gitea.artixlinux.org"
AUR_RPC_URL    = "https://aur.archlinux.org/rpc/v5"
AUR_CLONE_URL  = "https://aur.archlinux.org/{pkg}.git"
AUR_CACHE_TTL  = 3600   # seconds before AUR cache expires

# ── Artix GitLab (official PKGBUILDs) ────────────────────────
ARCH_GITLAB_URL = "https://gitea.artixlinux.org/packages"

# ── Package Format ───────────────────────────────────────────
PKG_EXTENSIONS = [".pkg.tar.zst", ".fin"]
PKGINFO_FILE   = ".PKGINFO"
INSTALL_FILE   = ".INSTALL"
MTREE_FILE     = ".MTREE"

# ── Supported Init Systems ───────────────────────────────────
# Selachii uses OpenRC. All three Artix init families are supported.
INIT_SYSTEMD  = "systemd"
INIT_SYSVINIT = "sysvinit"
INIT_OPENRC   = "openrc"
INIT_RUNIT    = "runit"
INIT_S6       = "s6"
SUPPORTED_INIT = [INIT_SYSTEMD, INIT_SYSVINIT, INIT_OPENRC, INIT_RUNIT, INIT_S6]

# ── Init → repo suffix mapping ───────────────────────────────
# Used to prioritize the right world-* repo for a given init system
INIT_REPO_SUFFIX = {
    INIT_OPENRC:   "world-openrc",
    INIT_RUNIT:    "world-runit",
    INIT_S6:       "world-s6",
    INIT_SYSVINIT: "world",   # no dedicated suffix; use base world
    INIT_SYSTEMD:  "world",
}

# ── DB Freshness ─────────────────────────────────────────────
DB_MAX_AGE_SECONDS = 86400   # 24 hours before stale warning

# ── Download ─────────────────────────────────────────────────
PARALLEL_DOWNLOADS  = 8
DOWNLOAD_CHUNK_SIZE = 4096
DOWNLOAD_TIMEOUT    = 120
MIRROR_BENCH_COUNT  = 5

# ── Security ─────────────────────────────────────────────────
GPG_KEYRING    = "/etc/pacman.d/gnupg"
MIN_SIG_LEVEL  = "required"

# ── Hook Scanner — dangerous patterns ────────────────────────
DANGEROUS_HOOK_PATTERNS = [
    "curl",
    "wget",
    "bash -c",
    "sh -c",
    "eval",
    "exec",
    "nc ",
    "ncat",
    "/dev/tcp",
    "base64 -d",
    "python -c",
    "perl -e",
    "ruby -e",
    "dd if",
    "mkfifo",
    "rm -rf /",
]
