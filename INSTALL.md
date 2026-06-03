# fin Installation Guide

This guide documents the current, supported installation flow for Fin on Selachii / LFS-style systems.

## 1. Prerequisites

Required runtime tools (validated by `install.sh`):

- `python3`
- `tar`
- `zstd`
- `gpg`
- `git`
- `fakeroot`
- `sudo`

For release-binary download fallback (when no local `dist/fin` exists):

- `wget` or `curl`

Notes:

- fin preflight expects Python `>= 3.9`.
- Install tools from your LFS/BLFS build as needed.

## 2. Recommended Installation

From repository root:

```bash
git clone https://github.com/LightNabz/fin.git
cd fin
sudo bash install.sh
```

What this does:

1. Verifies required tools.
2. Creates fin directories under `/etc/fin`, `/var/lib/fin`, `/var/cache/fin`, `/var/log/fin`.
3. Installs `/usr/bin/fin` (from local `dist/fin` if present, otherwise downloads release binary).
4. Runs adoption scripts (`adopt_lfs.py`, `adopt_blfs.py`) unless skipped.
5. Runs `fin sync` unless skipped.

## 3. Installer Options

```bash
sudo bash install.sh --help
```

Supported options:

- `-v`, `--verbose`: detailed execution output
- `--no-sync`, `--quick`: skip final `fin sync`
- `--skip-adopt`: skip adoption scripts
- `--fin-version <ver>`: download a specific fin release binary (example: `1.2.0`)

Examples:

```bash
sudo bash install.sh --quick
sudo bash install.sh --skip-adopt
sudo bash install.sh --fin-version 1.2.0
sudo bash install.sh --verbose
```

## 4. Manual Installation

If you prefer manual deployment:

```bash
# from repo root
cp dist/fin /usr/bin/fin
chmod +x /usr/bin/fin

mkdir -p /etc/fin
mkdir -p /var/lib/fin/{sync,installed,snapshots}
mkdir -p /var/cache/fin/pkgs
mkdir -p /var/log/fin
```

Then adopt your existing system packages:

```bash
PYTHONPATH=. python3 scripts/adopt_lfs.py
PYTHONPATH=. python3 scripts/adopt_blfs.py -y
```

## 5. Adoption Script Modes

LFS base adoption:

```bash
PYTHONPATH=. python3 scripts/adopt_lfs.py --dry-run
PYTHONPATH=. python3 scripts/adopt_lfs.py
```

BLFS auto-discovery adoption:

```bash
PYTHONPATH=. python3 scripts/adopt_blfs.py --dry-run
PYTHONPATH=. python3 scripts/adopt_blfs.py --min-score 8 --dry-run
PYTHONPATH=. python3 scripts/adopt_blfs.py -y
```

Options:

- `--dry-run`: preview only (no LocalDB writes)
- `--min-score <n>`: confidence threshold for BLFS matching
- `-y`, `--yes`: non-interactive confirmation

## 6. Post-Install Checks

Run:

```bash
fin version
fin sync
fin search bash
```

Useful version commands:

- `fin version`: fin/runtime/tooling status
- `fin check-version <pkg>`: package versions across local/sync/AUR/cache

## 7. Uninstall

Remove fin binary and state directories:

```bash
sudo rm -f /usr/bin/fin /usr/bin/fin.bin
sudo rm -rf /etc/fin /var/lib/fin /var/cache/fin /var/log/fin
```

This removes fin-managed metadata, cache, and logs.
