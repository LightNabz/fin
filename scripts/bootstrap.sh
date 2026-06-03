#!/bin/bash
# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  scripts/bootstrap.sh — bootstrap fin on a fresh LFS system
# ============================================================
#
#  This script gets fin running on a bare LFS installation.
#  It installs Python dependencies, creates directory structure,
#  and runs initial setup.
#
#  Usage:  sudo bash scripts/bootstrap.sh
# ============================================================

set -e

# ── Colors ───────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[fin]${NC} $1"; }
ok()    { echo -e "${GREEN}[  ✓ ]${NC} $1"; }
warn()  { echo -e "${YELLOW}[ !! ]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# ── Root check ───────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    fail "This script must be run as root (sudo bash scripts/bootstrap.sh)"
fi

echo ""
echo "  ╭──────────────────────────────────────────╮"
echo "  │        fin Bootstrap for Selachii       │"
echo "  │            Selachii Project © 2024              │"
echo "  ╰──────────────────────────────────────────╯"
echo ""

# ── Step 1: Check Python ────────────────────────────────────
info "Checking Python 3..."
if command -v python3 &> /dev/null; then
    PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    ok "Python ${PYVER} found"
else
    fail "Python 3 is not installed. Build Python >= 3.9 from LFS Chapter 8."
fi

# Check version >= 3.9
PYMAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYMINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PYMAJOR" -lt 3 ] || ([ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -lt 9 ]); then
    fail "Python >= 3.9 required (found ${PYVER})"
fi

# ── Step 2: Ensure pip is available ─────────────────────────
info "Checking pip..."
if ! python3 -m pip --version &> /dev/null; then
    info "pip not found. Bootstrapping via ensurepip..."
    python3 -m ensurepip --upgrade 2>/dev/null || {
        warn "ensurepip failed. Trying get-pip.py..."
        if command -v curl &> /dev/null; then
            curl -sS https://bootstrap.pypa.io/get-pip.py | python3
        elif command -v wget &> /dev/null; then
            wget -qO- https://bootstrap.pypa.io/get-pip.py | python3
        else
            fail "Cannot install pip. Install curl or wget first."
        fi
    }
fi
ok "pip available"

# ── Step 3: Install Python dependencies ─────────────────────
info "Installing Python dependencies..."
python3 -m pip install --quiet --break-system-packages \
    requests \
    python-gnupg \
    2>/dev/null || \
python3 -m pip install --quiet \
    requests \
    python-gnupg
ok "Python dependencies installed"

# ── Step 4: Check system tools ──────────────────────────────
info "Checking system tools..."

MISSING_TOOLS=""

for tool in git readelf tar zstd; do
    if command -v "$tool" &> /dev/null; then
        ok "$tool found"
    else
        warn "$tool NOT found"
        MISSING_TOOLS="$MISSING_TOOLS $tool"
    fi
done

if command -v gpg2 &> /dev/null || command -v gpg &> /dev/null; then
    ok "GPG found"
else
    warn "GPG not found (install gnupg2 from BLFS)"
    MISSING_TOOLS="$MISSING_TOOLS gpg"
fi

if [ -n "$MISSING_TOOLS" ]; then
    warn "Missing tools:$MISSING_TOOLS"
    warn "fin will work partially. Install missing tools from BLFS."
fi

# ── Step 5: Create directory structure ──────────────────────
info "Creating fin directories..."

mkdir -p /var/lib/fin/installed
mkdir -p /var/lib/fin/sync
mkdir -p /var/lib/fin/aur_cache
mkdir -p /var/lib/fin/snapshots
mkdir -p /var/cache/fin/pkgs
mkdir -p /var/cache/fin/aur
mkdir -p /var/log/fin
mkdir -p /etc/fin
mkdir -p /tmp/fin/aur
mkdir -p /tmp/fin/build

ok "Directory structure created"

# ── Step 6: Create default config if missing ────────────────
CONFIG="/etc/fin/fin.conf"
if [ ! -f "$CONFIG" ]; then
    info "Creating default config..."
    cat > "$CONFIG" << 'EOF'
[general]
install_root = /
cache_dir    = /var/cache/fin
db_path      = /var/lib/fin
log_file     = /var/log/fin/fin.log
init_system  = sysvinit

[repos]
use_official = true
use_aur      = true
aur_review   = prompt

[build]
build_dir         = /tmp/fin/aur
keep_cache        = true
parallel_jobs     = 4

[download]
parallel_downloads = 5
mirror             = auto

[upgrade]
ignored_packages =
held_packages    =
EOF
    ok "Default config created at ${CONFIG}"
else
    ok "Config already exists"
fi

# ── Step 7: Create default mirrorlist ───────────────────────
MIRRORLIST="/etc/fin/mirrorlist"
if [ ! -f "$MIRRORLIST" ]; then
    info "Creating default mirrorlist..."
    cat > "$MIRRORLIST" << 'EOF'
# fin Mirrorlist for Selachii
# Lines starting with # are comments.
# One mirror URL per line. Fastest mirrors first.
# Run 'fin mirror fastest' to auto-detect.
https://mirror.rackspace.com/archlinux
https://mirrors.kernel.org/archlinux
https://ftp.halifax.rwth-aachen.de/archlinux
https://mirror.aarnet.edu.au/pub/archlinux
https://mirrors.rit.edu/archlinux
EOF
    ok "Default mirrorlist created at ${MIRRORLIST}"
else
    ok "Mirrorlist already exists"
fi

# ── Step 8: Verify fin is importable ────────────────────────────────────────────────
info "Verifying fin module..."
FIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if PYTHONPATH="$FIN_DIR" python3 -c "import fin; print(f'fin {fin.constants.VERSION}')" 2>/dev/null; then
    ok "fin module verified"
else
    warn "Could not import fin module. Check installation."
fi

# ── Done ────────────────────────────────────────────────────
echo ""
echo "  ╭──────────────────────────────────────────╮"
echo "  │          Bootstrap Complete!              │"
echo "  ╰──────────────────────────────────────────╯"
echo ""
info "Next steps:"
echo "    1. Run 'fin sync' to download package databases"
echo "    2. Run 'fin mirror fastest' to find your fastest mirror"
echo "    3. Run 'fin preflight' to verify your environment"
echo ""
