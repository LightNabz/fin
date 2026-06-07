# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  resolver/systemd_filter.py — systemd dependency filtering
# ============================================================
#
#  On OpenRC/runit/s6 systems, hard systemd deps are replaced
#  with real Artix repo alternatives and queued for installation.
#  All alternatives here are verified packages in Artix repos.
# ============================================================

from typing import NamedTuple
from pathlib import Path

from ..exceptions import SystemdDependencyError

# ── Hard deps: will prevent the package from functioning ─────
SYSTEMD_HARD_DEPS = frozenset({
    "systemd",
    "systemd-libs",
    "systemd-sysvcompat",
    "systemd-resolvconf",
    "systemd-ukify",
})

# ── Soft deps: optional integration, safe to ignore ──────────
SYSTEMD_SOFT_INDICATORS = frozenset({
    "systemd-service",
    "systemctl",
})

# ── Real Artix repo alternatives ─────────────────────────────
# All verified against: world-openrc, world-runit, world-s6, system
# These will be QUEUED FOR INSTALL, not just name-swapped.
SYSTEMD_ALTERNATIVES = {
    "systemd-libs":       "elogind",
    "libsystemd":         "elogind",
    "libsystemd.so":      "elogind",
    "libsystemd.so=0-64": "elogind",
    "systemd-logind":     "elogind",
    "liblogind":          "elogind",
    "libudev.so":         "eudev",
    "libudev.so=1-0":     "eudev",
    "udev":               "eudev",
    # No alternative — block these entirely
    "systemd":            None,
    "systemd-sysvcompat": None,
}


class SystemdCheckResult(NamedTuple):
    safe:                  bool
    hard_deps:             list[str]
    soft_deps:             list[str]
    alternatives:          dict[str, str]   # dep → Artix package to install
    missing_alternatives:  list[str]        # hard deps with no known alternative
    source_build_advised:  bool


def check_systemd_deps(pkg_name: str, deps: list[str], init_system: str = "openrc") -> SystemdCheckResult:
    """
    Classify a package's dependencies for systemd contamination.

    Returns a result indicating which deps are hard/soft,
    what Artix alternatives exist, and whether the package is safe to install.
    """
    normalized_init = (init_system or "").strip().lower()

    # On actual systemd or in a detected systemd runtime — no filtering needed
    if Path("/run/systemd/private").exists() or normalized_init == "systemd":
        return SystemdCheckResult(
            safe=True, hard_deps=[], soft_deps=[],
            alternatives={}, missing_alternatives=[],
            source_build_advised=False,
        )

    hard_deps            = []
    soft_deps            = []
    alternatives         = {}
    missing_alternatives = []

    for dep in deps:
        # Strip version constraints: libfoo.so>=1 → libfoo.so
        dep_name = dep.split(">=")[0].split("<=")[0]\
                      .split(">")[0].split("<")[0]\
                      .split("=")[0].strip()

        if dep_name in SYSTEMD_HARD_DEPS:
            # Special case: pacman lists systemd for sysusers but works without it
            if pkg_name == "pacman" and dep_name == "systemd":
                continue
            hard_deps.append(dep_name)
            alt = SYSTEMD_ALTERNATIVES.get(dep_name)
            if alt:
                alternatives[dep_name] = alt
            else:
                missing_alternatives.append(dep_name)

        elif dep_name in SYSTEMD_SOFT_INDICATORS:
            soft_deps.append(dep_name)

        elif "libsystemd" in dep_name or "libudev" in dep_name:
            hard_deps.append(dep_name)
            alt = SYSTEMD_ALTERNATIVES.get(dep_name)
            if alt:
                alternatives[dep_name] = alt
            else:
                missing_alternatives.append(dep_name)

    safe = len(hard_deps) == 0
    source_advised = len(missing_alternatives) > 0

    return SystemdCheckResult(
        safe=safe,
        hard_deps=hard_deps,
        soft_deps=soft_deps,
        alternatives=alternatives,
        missing_alternatives=missing_alternatives,
        source_build_advised=source_advised,
    )


def resolve_systemd_deps(
    pkg_name:   str,
    deps:       list[str],
    init_system: str = "openrc",
    strict:     bool = True,
) -> tuple[list[str], list[str]]:
    """
    Resolve systemd dependencies for a package.

    Replaces hard systemd deps with their Artix alternatives in the dep list,
    and returns the list of alternative packages that need to be installed.

    Args:
        pkg_name:    Name of the package being resolved
        deps:        Full dependency list from the package DB
        init_system: Current init system
        strict:      If True, raise on hard deps with no alternative

    Returns:
        (clean_deps, to_install)
        - clean_deps:  dep list with systemd entries replaced/removed
        - to_install:  list of Artix alternative packages to queue for install
    """
    result   = check_systemd_deps(pkg_name, deps, init_system)
    to_install: list[str] = []
    clean_deps: list[str] = []

    for dep in deps:
        dep_name = dep.split(">=")[0].split("<=")[0]\
                      .split(">")[0].split("<")[0]\
                      .split("=")[0].strip()

        if dep_name in result.alternatives:
            alt = result.alternatives[dep_name]
            # Queue the alternative for installation
            if alt not in to_install:
                to_install.append(alt)
                print(f"   [systemd-filter] {dep_name} → {alt} (Artix repo)")
            # Don't add the original systemd dep to clean_deps
            continue

        if dep_name in result.missing_alternatives:
            if strict:
                raise SystemdDependencyError(pkg_name, [dep_name])
            print(f"   ⚠ [systemd-filter] {dep_name} has no alternative — skipping")
            continue

        if dep_name in SYSTEMD_SOFT_INDICATORS:
            # Soft dep — skip silently
            continue

        clean_deps.append(dep)

    return clean_deps, to_install


def filter_systemd_packages(
    packages:    list,
    init_system: str  = "openrc",
    strict:      bool = True,
) -> tuple[list, list[dict]]:
    """
    Filter a list of Package objects, blocking hard systemd deps.
    Returns (safe_packages, warnings).
    """
    safe     = []
    warnings = []

    for pkg in packages:
        result = check_systemd_deps(pkg.name, pkg.deps, init_system)

        if result.safe:
            safe.append(pkg)
            if result.soft_deps:
                warnings.append({
                    "package": pkg.name,
                    "level":   "info",
                    "message": f"Has optional systemd integration "
                               f"({', '.join(result.soft_deps)}) — safe on OpenRC",
                })
        else:
            if strict:
                raise SystemdDependencyError(pkg.name, result.hard_deps)

            alt_msg = ""
            if result.alternatives:
                alts    = [f"{k} → {v}" for k, v in result.alternatives.items()]
                alt_msg = f". Artix alternatives: {', '.join(alts)}"

            warnings.append({
                "package":      pkg.name,
                "level":        "blocked",
                "message":      f"Requires systemd: {', '.join(result.hard_deps)}{alt_msg}",
                "to_install":   list(result.alternatives.values()),
                "source_build": result.source_build_advised,
            })

    return safe, warnings
