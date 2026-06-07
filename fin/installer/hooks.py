# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  installer/hooks.py — Post-install package hooks & translation
# ============================================================
#
#  Reads `.INSTALL` scriptlets. Automatically translates Arch
#  `systemctl` commands into OpenRC / runit / s6 equivalents.
#  Runs global ldconfig and cache updates after each transaction.
# ============================================================

import os
import subprocess
from pathlib import Path

from ..config import get_config
from ..exceptions import HookError
from ..security.hook_scanner import scan_file, prompt_hook_approval

# Standard post-install hooks always run after any transaction
AUTO_HOOKS = [
    ["ldconfig"],
]

# ── Init translation tables ───────────────────────────────────

# systemctl action → OpenRC equivalent
# {service} is substituted at runtime
OPENRC_TRANSLATIONS = {
    "enable":       "rc-update add {service} default",
    "disable":      "rc-update del {service} default",
    "start":        "rc-service {service} start",
    "stop":         "rc-service {service} stop",
    "restart":      "rc-service {service} restart",
    "status":       "rc-service {service} status",
    "daemon-reload": ":",   # no-op on OpenRC
    "is-enabled":   "rc-update show default | grep -q {service}",
    "is-active":    "rc-service {service} status",
    "try-restart":  "rc-service {service} --ifstarted restart",
    "reload":       "rc-service {service} reload",
}

# systemctl action → runit equivalent
RUNIT_TRANSLATIONS = {
    "enable":       "ln -sf /etc/runit/sv/{service} /run/runit/service/{service}",
    "disable":      "rm -f /run/runit/service/{service}",
    "start":        "sv start {service}",
    "stop":         "sv stop {service}",
    "restart":      "sv restart {service}",
    "status":       "sv status {service}",
    "daemon-reload": ":",
    "is-enabled":   "[ -L /run/runit/service/{service} ]",
    "is-active":    "sv status {service}",
    "try-restart":  "sv restart {service}",
    "reload":       "sv reload {service}",
}

# systemctl action → s6 equivalent
S6_TRANSLATIONS = {
    "enable":       "s6-rc-bundle add default {service}",
    "disable":      "s6-rc-bundle del default {service}",
    "start":        "s6-rc -u change {service}",
    "stop":         "s6-rc -d change {service}",
    "restart":      "s6-rc -d change {service} && s6-rc -u change {service}",
    "status":       "s6-svstat /run/s6/supervise/{service}",
    "daemon-reload": ":",
    "is-enabled":   "s6-rc-bundle show default | grep -q {service}",
    "is-active":    "s6-svstat /run/s6/supervise/{service}",
    "try-restart":  "s6-rc -d change {service} && s6-rc -u change {service}",
    "reload":       "s6-svc -h /run/s6/supervise/{service}",
}

INIT_TRANSLATIONS = {
    "openrc":   OPENRC_TRANSLATIONS,
    "runit":    RUNIT_TRANSLATIONS,
    "s6":       S6_TRANSLATIONS,
    "sysvinit": OPENRC_TRANSLATIONS,   # close enough for LFS purposes
}


def run_auto_hooks(install_root: str = None):
    """Run standard system cache updates after a transaction."""
    root = install_root or get_config().install_root
    print("\n   [Hooks] Running global system updates...")
    for cmd in AUTO_HOOKS:
        try:
            subprocess.run(
                cmd,
                cwd=root if root != "/" else None,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            print(f"      ⚠ '{cmd[0]}' timed out and was skipped.")
        except (FileNotFoundError, OSError):
            continue


class HookRunner:
    def __init__(self, pkg_name: str, install_file: str, is_aur: bool = False):
        self.pkg_name     = pkg_name
        self.install_file = install_file
        self.is_aur       = is_aur
        self.config       = get_config()
        self._in_chroot   = self._detect_chroot()

    def _detect_chroot(self) -> bool:
        if Path("/run/systemd/private").exists():
            return False
        try:
            root_stat     = os.stat("/")
            pid1_root_stat = os.stat("/proc/1/root/.")
            return (root_stat.st_dev, root_stat.st_ino) != (
                pid1_root_stat.st_dev, pid1_root_stat.st_ino
            )
        except OSError:
            return True

    # ── Public ────────────────────────────────────────────────

    def run_phase(self, phase: str, version: str, old_version: str = ""):
        """
        Execute a specific phase function from the .INSTALL scriptlet.
        Translates systemctl calls to the configured init system.
        """
        path = Path(self.install_file)
        if not path.exists():
            return

        # Security scan
        scan_result = scan_file(str(path))
        if not scan_result.safe:
            if self.is_aur:
                action = prompt_hook_approval(self.pkg_name, scan_result)
                if action == "A":
                    raise HookError(
                        f"Install aborted by user due to security warnings in {self.pkg_name}."
                    )
                elif action == "S":
                    print(f"   [Hooks] Skipping {phase} for {self.pkg_name} due to security concerns.")
                    return
                # action "R" → continue
            # Official packages: auto-approve

        script_content    = path.read_text(errors="replace")
        translated_content = self._translate_init_commands(script_content)

        # Build systemd chroot shim if needed
        systemctl_shim = ""
        if self.config.init_system == "systemd" and self._in_chroot:
            systemctl_shim = self._systemd_chroot_shim()

        runner_script = path.with_name(f".{self.pkg_name}_{phase}.sh")
        bash_wrapper  = (
            f"#!/bin/bash\n"
            f"# Hook wrapper generated by fin — {self.pkg_name} ({phase})\n"
            f"{systemctl_shim}\n"
            f"{translated_content}\n"
            f"\nif type {phase} >/dev/null 2>&1; then\n"
            f"    {phase} {version} {old_version}\n"
            f"fi\n"
        )
        runner_script.write_text(bash_wrapper)
        runner_script.chmod(0o755)

        print(f"   [Hooks] Running {phase} for {self.pkg_name}...")
        try:
            result = subprocess.run(
                [str(runner_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=os.environ.copy(),
                timeout=120,
            )
            if result.stdout.strip():
                self._log_hook_output(phase, result.stdout)
            if result.returncode != 0:
                print(f"   ⚠ Hook {phase} returned non-zero ({result.returncode})")
        except subprocess.TimeoutExpired:
            print(f"   ⚠ Hook {phase} timed out after 120s")
        finally:
            if runner_script.exists():
                runner_script.unlink()

    # ── Translation ───────────────────────────────────────────

    def _translate_init_commands(self, script: str) -> str:
        """
        Translate all systemctl calls in a .INSTALL scriptlet to the
        configured init system (OpenRC, runit, s6).
        No-ops on systemd unless we're in a chroot.
        """
        init_sys = self.config.init_system
        if init_sys == "systemd" and not self._in_chroot:
            return script  # no translation needed

        table = INIT_TRANSLATIONS.get(init_sys, OPENRC_TRANSLATIONS)
        lines = script.splitlines()
        return "\n".join(self._translate_line(line, table) for line in lines)

    def _translate_line(self, line: str, table: dict) -> str:
        """Translate a single line if it contains a systemctl call."""
        stripped = line.strip()

        # Skip comments and lines with no systemctl
        if stripped.startswith("#") or "systemctl" not in stripped:
            return line

        parts = stripped.split()
        if "systemctl" not in parts:
            return line

        idx = parts.index("systemctl")
        if idx + 1 >= len(parts):
            return line

        action  = parts[idx + 1]
        service = parts[idx + 2] if idx + 2 < len(parts) else ""

        # Strip .service suffix
        service = service.removesuffix(".service")

        translation = table.get(action)
        if translation is None:
            # Unknown action — neutralize safely
            print(f"   [Hooks] Unsupported systemctl action '{action}' — skipping")
            return f": # fin: unsupported systemctl {action} {service}"

        translated = translation.format(service=service)

        # Reconstruct: everything before `systemctl` + translated cmd + remainder
        prefix  = " ".join(parts[:idx])
        suffix  = " ".join(parts[idx + 3:]) if idx + 3 < len(parts) else ""
        result  = " ".join(filter(None, [prefix, translated, suffix]))

        # Preserve original indentation
        indent  = len(line) - len(line.lstrip())
        return " " * indent + result

    # ── Systemd chroot shim ───────────────────────────────────

    def _systemd_chroot_shim(self) -> str:
        """
        Bash function that stubs out systemctl in a systemd chroot
        where the daemon isn't running.
        """
        return """\
systemctl() {
    local action="$1" service="${2%.service}"
    case "$action" in
        enable)
            mkdir -p /etc/systemd/system/multi-user.target.wants
            ln -sf "/usr/lib/systemd/system/${service}.service" \\
                   "/etc/systemd/system/multi-user.target.wants/${service}.service"
            ;;
        start|stop|restart|status|disable|daemon-reload|is-active|is-enabled)
            :
            ;;
        *)
            :
            ;;
    esac
}"""

    # ── Logging ───────────────────────────────────────────────

    def _log_hook_output(self, phase: str, output: str):
        from ..constants import LOG_HOOKS
        log_path = Path(LOG_HOOKS)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a") as f:
                f.write(f"\n--- {self.pkg_name} ({phase}) ---\n")
                f.write(output)
                f.write("\n")
        except OSError:
            pass
