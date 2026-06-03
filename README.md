# fin

**fin** is the package manager for [Selachii](https://github.com/LightNabz/selachii) — an OpenRC-based Linux From Scratch distribution.

fin pulls packages from **Artix Linux** official repositories and the Arch AUR, giving you access to a vast software ecosystem while keeping your system completely free of systemd.

---

## Background

fin is a fork of [sven](https://github.com/haroldmth/sven) by HaroldMth, originally written for Seven OS.

The upstream project had the right idea — a package manager purpose-built for non-systemd LFS systems, with protected base packages, rollback snapshots, and smart systemd dependency filtering. However, it shipped with several fundamental issues:

- Targeting **Arch Linux** repos on a non-systemd system, meaning `libsystemd` and `libudev` alternatives it listed (`elogind`, `eudev`) **do not exist in Arch's repos** and would silently fail
- A broken release pipeline — the install script downloads a binary that was never uploaded, `sven.spec` was never committed, and runtime dependencies are not declared
- Adoption scripts buried in section C of the docs, despite being a **required first step** before any package install
- Various spaghetti in the resolver's dependency graph causing unrelated protected packages to be touched during normal installs

fin fixes all of this by switching to **Artix Linux** as its repo source, where `elogind`, `eudev`, and all other systemd alternatives are first-class, maintained packages across `world-openrc`, `world-runit`, and `world-s6` repos.

---

## Features

- **Zero-contamination installs** — hard systemd dependencies are blocked; soft ones (`.service` files) are allowed through safely
- **Artix repo support** — `world`, `world-openrc`, `world-runit`, `world-s6`, `system`, `lib32`
- **OpenRC, runit, and s6** init families all supported
- **Protected LFS base packages** — core toolchain and system libraries cannot be accidentally removed or replaced
- **Rollback snapshots** — every transaction is snapshotted; rollback with one command
- **AUR support** — full Arch AUR build and install flow
- **LFS/BLFS adoption** — register your existing LFS build into fin's LocalDB before installing anything new
- **Mirror benchmarking** — automatically picks the fastest Artix mirror
- **GLIBC ABI checking** — deep binary compatibility checks using `readelf` before installing

---

## ⚠️ Run adoption scripts first

Before installing any package, you **must** run the adoption scripts once. Without this, fin does not know what is already installed on your LFS base system and will attempt to resolve and reinstall core packages, tripping protected package guards.

```bash
PYTHONPATH=. python3 scripts/adopt_lfs.py
PYTHONPATH=. python3 scripts/adopt_blfs.py
```

You only need to do this once after the initial install. Preview changes first with `--dry-run`:

```bash
PYTHONPATH=. python3 scripts/adopt_lfs.py --dry-run
PYTHONPATH=. python3 scripts/adopt_blfs.py --min-score 8 --dry-run
```

---

## Install

```bash
git clone https://github.com/LightNabz/fin.git
cd fin
sudo bash install.sh
```

Since fin is a Python project, it can also be run directly without building a binary:

```bash
pip install requests zstandard python-gnupg --break-system-packages
python3 run_fin.py --help
```

To build the standalone binary:

```bash
make dev
make build
# binary will be at dist/fin
sudo cp dist/fin /usr/bin/fin
```

### Installer options

```bash
sudo bash install.sh --help
```

| Flag | Description |
|------|-------------|
| `--no-sync` / `--quick` | Skip final `fin sync` (run manually when online) |
| `--verbose` | Detailed execution output |

---

## Core commands

```bash
fin install <pkg ...>              # install packages
fin install <pkg> --version <ver>  # install a specific version
fin remove <pkg ...>               # remove packages
fin upgrade                        # full system upgrade
fin sync                           # refresh package databases
fin search <query>                 # search repos + AUR
fin info <pkg>                     # package metadata
fin deps <pkg>                     # dependency tree
fin check-version <pkg>            # compare installed/sync/AUR/cache versions
fin mirror benchmark               # find fastest Artix mirror
fin snapshots                      # list rollback snapshots
fin rollback <snapshot>            # undo a transaction
fin doctor                         # system health check
fin version                        # show fin + runtime tool versions
```

---

## Paths

| Path | Purpose |
|------|---------|
| `/etc/fin/fin.conf` | Configuration file (auto-created on first run) |
| `/etc/fin/mirrorlist` | Manual mirror override |
| `/var/lib/fin/` | Package databases |
| `/var/cache/fin/pkgs/` | Downloaded package cache |
| `/var/log/fin/` | Logs |

---

## Configuration

`/etc/fin/fin.conf` is created automatically on first run with sensible defaults for Selachii. Key options:

```ini
[general]
init_system = openrc   # openrc | runit | s6 | sysvinit

[repos]
use_official = true
use_aur      = true
aur_review   = prompt  # always | prompt | never

[safety]
# Space-separated list of packages fin will never touch without --force-protected
protected_packages = glibc linux-api-headers filesystem gcc ...
```

---

## License

GPL v3 — see [LICENSE](LICENSE).

Forked from [sven](https://github.com/haroldmth/sven) by HaroldMth, also GPL v3.