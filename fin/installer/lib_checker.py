# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  installer/lib_checker.py — Verify required shared libraries
# ============================================================
#
#  Checks if all required .so dependencies are present on the
#  LFS host before extracting a package.
#  Scans standard paths AND subdirectories (e.g. /usr/lib/elogind/)
#  so that libraries installed in non-standard locations are found.
# ============================================================

import os
from pathlib import Path

from ..config import get_config
from ..exceptions import MissingLibraryError

# Standard lib paths — checked in order, including one level of subdirs
LIB_PATHS = [
    "/usr/lib",
    "/usr/lib64",
    "/lib",
    "/lib64",
    "/usr/local/lib",
]

# Known non-standard subdirectory locations for specific libraries.
# This covers packages that install their private .so under a subdirectory
# but still need to be considered "present" for dep resolution.
# Format: lib_prefix → [subdir, ...]
KNOWN_SUBDIRS = {
    "libelogind": ["elogind"],
    "libudev":    ["udev", "eudev"],
    "libGL":      ["dri", "mesa"],
    "libEGL":     ["dri", "mesa"],
    "libvulkan":  ["vulkan"],
}


class LibChecker:
    def __init__(self, custom_lib_paths: list[str] = None):
        self.config    = get_config()
        self.lib_paths = custom_lib_paths or LIB_PATHS

        # Adjust all paths for alternate install root
        if self.config.install_root != "/":
            self.lib_paths = [self.config.rooted(p) for p in self.lib_paths]

        # Build full subdir scan list — base paths + one level of known subdirs
        self._scan_paths = self._build_scan_paths()

    def _build_scan_paths(self) -> list[Path]:
        """
        Build the full list of paths to scan.
        Includes base lib paths + one level of subdirectories.
        Skips non-existent paths silently.
        """
        paths = []
        for base in self.lib_paths:
            p = Path(base)
            if p.exists():
                paths.append(p)
                # Include one level of subdirs
                try:
                    for sub in p.iterdir():
                        if sub.is_dir():
                            paths.append(sub)
                except PermissionError:
                    pass
        return paths

    def check_package(self, pkg_name: str, required_libs: list[str]) -> bool:
        """
        Verify that all required .so files exist on the filesystem.

        Args:
            pkg_name:      The name of the package being checked.
            required_libs: List of .so filenames (e.g. ['libssl.so.3', 'libelogind.so.0'])

        Returns:
            True if all libs are found.

        Raises:
            MissingLibraryError if any lib is completely absent.
        """
        missing = []
        for lib in required_libs:
            if not self._lib_exists(lib):
                missing.append(lib)

        if missing:
            raise MissingLibraryError(missing[0], pkg_name)

        return True

    def find_lib(self, lib_name: str) -> Path | None:
        """
        Find the actual path of a library file on disk.
        Returns the Path if found, None otherwise.
        """
        for path in self._scan_paths:
            candidate = path / lib_name
            if candidate.exists():
                return candidate

            # Try base .so fallback (libfoo.so.1 → libfoo.so)
            base_so = lib_name.split(".so")[0] + ".so"
            if base_so != lib_name:
                base_path = path / base_so
                if base_path.exists():
                    return base_path

        # Try known subdir hints for this lib
        prefix = lib_name.split(".so")[0]
        for known_prefix, subdirs in KNOWN_SUBDIRS.items():
            if lib_name.startswith(known_prefix):
                for base in self.lib_paths:
                    for subdir in subdirs:
                        candidate = Path(base) / subdir / lib_name
                        if candidate.exists():
                            return candidate
        return None

    def _lib_exists(self, lib_name: str) -> bool:
        """Return True if the library exists anywhere in the scan paths."""
        return self.find_lib(lib_name) is not None

    def missing_libs(self, required_libs: list[str]) -> list[str]:
        """Return a list of libs from required_libs that are missing on disk."""
        return [lib for lib in required_libs if not self._lib_exists(lib)]

    def create_missing_symlinks(self, extracted_files: list[str]) -> list[str]:
        """
        After extraction, ensure public .so symlinks exist for any library
        that was installed into a non-standard subdirectory.

        For example, if /usr/lib/elogind/libelogind-shared-257.so was extracted
        but /usr/lib/libelogind.so.0 doesn't exist, create the symlink.

        Returns list of symlinks created.
        """
        created = []

        for file_path in extracted_files:
            p = Path(file_path)
            if not p.suffix == ".so" and ".so." not in p.name:
                continue

            # Check if this is a private .so in a subdirectory
            parent = p.parent
            grandparent = parent.parent

            # Only act on files two levels deep under a lib path
            # e.g. /usr/lib/elogind/libelogind-shared-257.14-4.so
            if grandparent.name not in ("lib", "lib64", "usr"):
                if not any(str(grandparent) == base for base in self.lib_paths):
                    continue

            lib_name = p.name

            # Derive the public soname from the private filename
            # e.g. libelogind-shared-257.14-4.so → libelogind.so.0
            public_name = self._derive_public_soname(lib_name)
            if not public_name:
                continue

            # Check if the public symlink already exists anywhere
            if self._lib_exists(public_name):
                continue

            # Create symlink in /usr/lib/
            symlink_target = grandparent / public_name
            try:
                if not symlink_target.exists() and not symlink_target.is_symlink():
                    symlink_target.symlink_to(p)
                    created.append(str(symlink_target))
                    print(f"   [LibChecker] Created symlink: {symlink_target} → {p}")
            except OSError as e:
                print(f"   ⚠ [LibChecker] Could not create symlink {symlink_target}: {e}")

        return created

    def _derive_public_soname(self, private_name: str) -> str | None:
        """
        Derive the public soname from a private library filename.
        Handles common patterns:
          libelogind-shared-257.14-4.so → libelogind.so.0
          libudev-private-1.2.3.so      → libudev.so.1
        Returns None if no mapping can be derived.
        """
        SONAME_MAP = {
            "libelogind": ("libelogind.so.0",  "elogind"),
            "libudev":    ("libudev.so.1",     "eudev"),
        }
        for prefix, (public_name, _) in SONAME_MAP.items():
            if private_name.startswith(prefix):
                return public_name
        return None
