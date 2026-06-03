# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  downloader/mirror.py — mirror discovery, benchmarking, failover
# ============================================================

import json
import logging
import socket
import time
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import urlparse

from ..constants import (
    ARTIX_MIRROR_LIST_URL,
    DEFAULT_MIRROR,
    DB_BASE,
    CONFIG_DIR,
    MIRROR_BENCH_COUNT,
    DOWNLOAD_TIMEOUT,
)
from ..exceptions import MirrorError, MirrorTimeoutError


MIRROR_CACHE_FILE = f"{DB_BASE}/mirrors.json"
MIRRORLIST_FILE   = f"{CONFIG_DIR}/mirrorlist"

logger = logging.getLogger("fin")


def _url_resolves_to_loopback(url: str) -> bool:
    try:
        host = urlparse(url).hostname
    except Exception:
        return False
    if not host:
        return False
    h = host.lower()
    if h in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        ip = info[4][0]
        if ip not in ("127.0.0.1", "::1") and not ip.startswith("127."):
            return False
    return True


def _strip_loopback_mirrors(
    mirrors: list[dict],
    *,
    max_dns_check: int = 120,
) -> list[dict]:
    if not mirrors:
        return mirrors

    head_n = min(max_dns_check, len(mirrors))
    head, tail = mirrors[:head_n], mirrors[head_n:]

    def check_mirror(m):
        u = m.get("url") or ""
        if _url_resolves_to_loopback(u):
            return None
        return m

    kept: list[dict] = []
    with ThreadPoolExecutor(max_workers=32) as executor:
        results = list(executor.map(check_mirror, head))
        for res in results:
            if res:
                kept.append(res)

    out = kept + tail
    if not out:
        return [{"url": DEFAULT_MIRROR, "country": "Default", "score": 0, "ping_ms": None}]

    dropped = head_n - len(kept)
    if dropped and not tail:
        logger.info("Removed %d loopback mirror(s); using public mirrors.", dropped)
    return out


class MirrorManager:
    """
    Discovers, benchmarks, and manages Artix Linux mirrors.
    Parses the official Artix mirrorlist and provides automatic failover.
    """

    def __init__(self, cache_path: str = MIRROR_CACHE_FILE):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._mirrors: list[dict] = []
        self._current_index: int = 0
        self._blacklist: set[str] = set()
        self._parallel_dl_depth: int = 0

    @property
    def mirrors(self) -> list[dict]:
        if not self._mirrors:
            self._load_cached()
        if not self._mirrors:
            self._mirrors = self.fetch_mirror_list()
            self._save_cached(self._mirrors)
        return self._mirrors

    @property
    def current(self) -> str:
        if self.cache_path != Path(MIRROR_CACHE_FILE):
            if not self._mirrors:
                return DEFAULT_MIRROR
        self.mirrors
        if not self._mirrors:
            return DEFAULT_MIRROR

        while self._mirrors[self._current_index]["url"] in self._blacklist:
            self._current_index += 1
            if self._current_index >= len(self._mirrors):
                self._current_index = 0
                break

        return self._mirrors[self._current_index]["url"]

    def begin_parallel_downloads(self) -> None:
        self._parallel_dl_depth += 1

    def end_parallel_downloads(self) -> None:
        self._parallel_dl_depth = max(0, self._parallel_dl_depth - 1)

    def _downloads_ui_active(self) -> bool:
        return self._parallel_dl_depth > 0

    def next_mirror(self) -> str:
        self._current_index += 1
        if self._current_index >= len(self._mirrors):
            raise MirrorError("All mirrors exhausted. No more mirrors to try.")
        url = self._mirrors[self._current_index]["url"]
        if url in self._blacklist:
            return self.next_mirror()
        if not self._downloads_ui_active():
            print(f"   ⟳ Failing over to: {url}")
        return url

    def blacklist_current(self):
        url = self.current
        if url not in self._blacklist:
            if not self._downloads_ui_active():
                print(f"   ⚠ Blacklisting unreliable mirror: {url}")
            self._blacklist.add(url)

    def reset(self):
        self._current_index = 0

    # ── Fetch Mirror List ────────────────────────────────────

    def fetch_mirror_list(self) -> list[dict]:
        """
        Fetch the Artix Linux mirrorlist from the official Gitea repo.
        Parses the mirrorlist format (Server = https://...) directly.
        Falls back to /etc/fin/mirrorlist, then cached mirrors, then default.
        """
        print("   Fetching mirror list from artixlinux.org...")
        try:
            resp = requests.get(ARTIX_MIRROR_LIST_URL, timeout=DOWNLOAD_TIMEOUT)
            resp.raise_for_status()
            mirrors = self._parse_mirrorlist_text(resp.text)
            if mirrors:
                return _strip_loopback_mirrors(mirrors)
            raise ValueError("Empty mirror list parsed")
        except (requests.RequestException, ValueError) as e:
            print(f"   ⚠ Mirror list unreachable: {e}")
            # Fallback 1: manual mirrorlist
            if self.cache_path == Path(MIRROR_CACHE_FILE):
                manual = self._load_from_mirrorlist()
                if manual:
                    print(f"   ↳ Using /etc/fin/mirrorlist ({len(manual)} mirrors)")
                    return manual
            # Fallback 2: cached
            self._load_cached()
            if self._mirrors:
                print(f"   ↳ Using cached mirror list ({len(self._mirrors)} mirrors)")
                return self._mirrors
            # Fallback 3: hardcoded default
            print("   ↳ Using default mirror")
            return [{"url": DEFAULT_MIRROR, "country": "Default", "score": 0, "ping_ms": None}]

    def _parse_mirrorlist_text(self, text: str) -> list[dict]:
        """
        Parse an Artix mirrorlist file.
        Format:
            # Some Country
            Server = https://mirror.example.com/artix-linux/$repo/os/$arch
        """
        mirrors = []
        current_country = "Unknown"
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                # Country headers look like: "# Worldwide" or "# Germany"
                candidate = line.lstrip("#").strip()
                if candidate and not any(c in candidate for c in ["=", "http", "Generated"]):
                    current_country = candidate
                continue
            if line.lower().startswith("server"):
                # Strip "Server = " prefix and the $repo/$arch suffix template
                url = line.split("=", 1)[-1].strip()
                # Normalize: remove trailing /$repo/os/$arch
                url = url.split("/$repo")[0].rstrip("/")
                if url.startswith("https://"):
                    mirrors.append({
                        "url":     url,
                        "country": current_country,
                        "score":   0,
                        "ping_ms": None,
                    })
        return mirrors

    def _load_from_mirrorlist(self) -> list[dict]:
        path = Path(MIRRORLIST_FILE)
        if not path.exists():
            return []
        mirrors = []
        try:
            with open(path) as f:
                mirrors = self._parse_mirrorlist_text(f.read())
        except OSError:
            pass
        return _strip_loopback_mirrors(mirrors)

    # ── Benchmark ────────────────────────────────────────────

    def benchmark_all(self) -> list[dict]:
        return self.benchmark()

    def benchmark(self, count: int = MIRROR_BENCH_COUNT) -> list[dict]:
        """
        Benchmark mirrors by timing a HEAD request against world.db.
        """
        all_mirrors = self.fetch_mirror_list()
        candidates = all_mirrors[:max(count * 3, 15)]

        print(f"   Benchmarking {len(candidates)} mirrors...")
        results = []

        for m in candidates:
            url = m["url"]
            test_url = f"{url}/world/os/x86_64/world.db"
            try:
                start = time.monotonic()
                resp = requests.head(test_url, timeout=5, allow_redirects=True)
                elapsed = (time.monotonic() - start) * 1000
                resp.raise_for_status()
                m["ping_ms"] = round(elapsed, 1)
                results.append(m)
                print(f"   {m['country']:>20s}  {url:<55s}  {elapsed:6.1f} ms")
            except requests.RequestException:
                print(f"   {m['country']:>20s}  {url:<55s}  TIMEOUT")
                continue

        results.sort(key=lambda m: m["ping_ms"])
        best = _strip_loopback_mirrors(results[:count])
        self._mirrors = best
        self._current_index = 0
        self._save_cached(best)

        if best:
            print(f"\n   ★ Fastest mirror: {best[0]['url']} ({best[0]['ping_ms']} ms)")
        else:
            print("   ⚠ No mirrors responded. Using default.")
            self._mirrors = [{"url": DEFAULT_MIRROR, "country": "Default", "score": 0, "ping_ms": 0}]

        return best

    def list_mirrors(self) -> list[dict]:
        self._load_cached()
        if self._mirrors:
            return self._mirrors
        all_mirrors = self.fetch_mirror_list()
        return all_mirrors[:20]

    # ── Cache ────────────────────────────────────────────────

    def _load_cached(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path) as f:
                    raw = json.load(f)
                if not isinstance(raw, list):
                    raw = []
                before = len(raw)
                self._mirrors = _strip_loopback_mirrors(raw)
                self._current_index = 0
                if before and len(self._mirrors) < before:
                    self._save_cached(self._mirrors)
            except (json.JSONDecodeError, OSError):
                self._mirrors = []

    def _save_cached(self, mirrors: list[dict]):
        try:
            with open(self.cache_path, "w") as f:
                json.dump(mirrors, f, indent=2)
        except OSError:
            pass
