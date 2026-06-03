# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  resolver/systemd_filter.py — systemd dependency filtering
# ============================================================
#
#  Selachii uses OpenRC. Many packages depend on systemd
#  components. This module classifies those dependencies and
#  blocks hard systemd requirements while allowing soft ones.
#
#  Unlike the upstream sven implementation, alternatives here
#  are real packages that exist in Artix's official repos.
#
#  This is still a bit problematic, but don't touch it if it's working :v
#
# ============================================================

from typing import NamedTuple
from pathlib import Path

from ..db.models import Package
from ..exceptions import SystemdDependencyError


# ── Known systemd packages and libraries ─────────────────────

# HARD deps: the package links against systemd or requires it to function
SYSTEMD_HARD_DEPS = frozenset({
    "systemd",
    "systemd-libs",
    "systemd-sysvcompat",
    "systemd-resolvconf",
    "systemd-ukify",
})

# SOFT deps: the package ships .service files or optional integration
# These are safe to install — the unit files just won't be used
SYSTEMD_SOFT_INDICATORS = frozenset({
    "systemd-service",
    "systemctl",
})

# Artix repo alternatives for systemd components.
# All entries here are real packages available in Artix's official repos.
# Verified against: world-openrc, world-runit, world-s6, system
SYSTEMD_ALTERNATIVES = {
    # libsystemd compatibility is provided by elogind on Artix
    "systemd-libs":       "elogind",         # world-openrc / world-runit / world-s6
    "libsystemd":         "elogind",
    "libsystemd.so":      "elogind",
    "libsystemd.so=0-64": "elogind",
    # udev is provided by eudev on Artix (in the 'system' repo)
    "libudev.so":         "eudev",            # system repo
    "libudev.so=1-0":     "eudev",
    "udev":               "eudev",
    # login/session management
    "systemd-logind":     "elogind",
    "liblogind":          "elogind",
    # no drop-in alternative for the full init
    "systemd":            None,
    "systemd-sysvcompat": None,
}


class SystemdCheckResult(NamedTuple):
    """Result of checking a package for systemd dependencies."""
    safe: bool                    # True if package is safe to install
    hard_deps: list[str]          # systemd deps that will prevent function
    soft_deps: list[str]          # systemd deps that are optional/ignorable
    alternatives: dict[str, str]  # Artix repo alternative for each hard dep
    source_build_advised: bool    # should we build from source instead?


def check_systemd_deps(pkg: Package, init_system: str = "openrc") -> SystemdCheckResult:
    """
    Check if a package has dependencies on systemd components.

    On OpenRC/runit/s6 systems, hard systemd deps mean the package
    won't function correctly. Soft deps (like .service files) are fine.

    Args:
        pkg: The package to check
        init_system: Current init system (openrc, runit, s6, sysvinit, systemd)

    Returns:
        SystemdCheckResult with classification
    """
    normalized_init = (init_system or "").strip().lower()

    runtime_systemd = Path("/run/systemd/private").exists()

    # If we're on systemd (configured or detected), everything is fine
    if runtime_systemd or normalized_init == "systemd" or normalized_init.startswith("systemd-"):
        return SystemdCheckResult(
            safe=True, hard_deps=[], soft_deps=[],
            alternatives={}, source_build_advised=False,
        )

    all_deps = pkg.deps
    hard_deps = []
    soft_deps = []
    alternatives = {}

    for dep in all_deps:
        # Strip version constraints
        dep_name = dep.split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].split("=")[0].strip()

        if dep_name in SYSTEMD_HARD_DEPS:
            # pacman declares "systemd" for sysusers hook but works fine without it
            if pkg.name == "pacman" and dep_name == "systemd":
                continue

            hard_deps.append(dep_name)
            alt = SYSTEMD_ALTERNATIVES.get(dep_name)
            if alt:
                alternatives[dep_name] = alt

        elif dep_name in SYSTEMD_SOFT_INDICATORS:
            soft_deps.append(dep_name)

        elif "libsystemd" in dep_name or "libudev" in dep_name:
            hard_deps.append(dep_name)
            alt = SYSTEMD_ALTERNATIVES.get(dep_name)
            if alt:
                alternatives[dep_name] = alt

    safe = len(hard_deps) == 0
    source_advised = len(hard_deps) > 0 and len(alternatives) < len(hard_deps)

    return SystemdCheckResult(
        safe=safe,
        hard_deps=hard_deps,
        soft_deps=soft_deps,
        alternatives=alternatives,
        source_build_advised=source_advised,
    )


def filter_systemd_packages(
    packages: list[Package],
    init_system: str = "openrc",
    strict: bool = True,
) -> tuple[list[Package], list[dict]]:
    """
    Filter a list of packages, removing those with hard systemd deps.

    Args:
        packages: List of packages to filter
        init_system: Current init system
        strict: If True, raise SystemdDependencyError on hard deps.
                If False, just warn and exclude.

    Returns:
        (safe_packages, warnings)
    """
    safe = []
    warnings = []

    for pkg in packages:
        result = check_systemd_deps(pkg, init_system)

        if result.safe:
            safe.append(pkg)
            if result.soft_deps:
                warnings.append({
                    "package": pkg.name,
                    "level": "info",
                    "message": f"Has optional systemd integration "
                               f"({', '.join(result.soft_deps)}) — safe to ignore on OpenRC",
                })
        else:
            if strict:
                raise SystemdDependencyError(pkg.name, result.hard_deps)

            alt_msg = ""
            if result.alternatives:
                alts = [f"{k} → {v} (Artix repo)" for k, v in result.alternatives.items()]
                alt_msg = f". Artix alternatives: {', '.join(alts)}"

            warnings.append({
                "package": pkg.name,
                "level": "blocked",
                "message": f"Requires systemd: {', '.join(result.hard_deps)}"
                           f"{alt_msg}",
                "source_build": result.source_build_advised,
            })

    return safe, warnings
