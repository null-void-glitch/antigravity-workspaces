"""
rss.py — RSS feed fetching, caching, and management.

Feeds are persisted to ~/.config/DesktopPet/rss_feeds.json.
Fetched items are cached for 15 minutes in ~/.config/DesktopPet/rss_cache/.

Pure logic — ported near-verbatim from the original rss_service.py.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any

import feedparser

from pet.config import CONFIG_DIR

log = logging.getLogger(__name__)

FEEDS_FILE = CONFIG_DIR / "rss_feeds.json"
CACHE_DIR = CONFIG_DIR / "rss_cache"
CACHE_TTL_SECONDS = 15 * 60

DEFAULT_FEEDS: list[str] = [
    "https://www.bleepingcomputer.com/feed/",
]


class RSSFeedManager:
    """Manages a list of RSS feed URLs, fetches items, and caches results."""

    def __init__(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._feeds: list[str] = self._load_feeds()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load_feeds(self) -> list[str]:
        if FEEDS_FILE.exists():
            try:
                data = json.loads(FEEDS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    return [str(u) for u in data]
            except (json.JSONDecodeError, OSError):
                pass
        # First run — seed defaults and persist them.
        self._persist(DEFAULT_FEEDS)
        return list(DEFAULT_FEEDS)

    def _persist(self, feeds: list[str]) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            FEEDS_FILE.write_text(
                json.dumps(feeds, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            log.warning("Could not persist RSS feeds: %s", exc)

    # ── Registry ──────────────────────────────────────────────────────────

    def list_feeds(self) -> list[str]:
        """Return the configured feed URLs."""
        return list(self._feeds)

    def add_feed(self, url: str) -> bool:
        """Add a feed URL; returns True if it wasn't already present."""
        url = url.strip().rstrip("/")
        if url and url not in self._feeds:
            self._feeds.append(url)
            self._persist(self._feeds)
            return True
        return False

    def remove_feed(self, url: str) -> bool:
        """Remove a feed URL; returns True if it existed."""
        url = url.strip().rstrip("/")
        if url in self._feeds:
            self._feeds.remove(url)
            self._persist(self._feeds)
            return True
        url_slash = url + "/"
        if url_slash in self._feeds:
            self._feeds.remove(url_slash)
            self._persist(self._feeds)
            return True
        return False

    def set_feeds(self, feeds: list[str]) -> None:
        """Replace the entire feed list."""
        self._feeds = [u.strip() for u in feeds if u.strip()]
        self._persist(self._feeds)

    # ── Caching ───────────────────────────────────────────────────────────

    @staticmethod
    def _cache_path(url: str):
        key = hashlib.sha256(url.encode()).hexdigest()[:16]
        return CACHE_DIR / f"{key}.json"

    def _read_cache(self, url: str) -> list[dict] | None:
        path = self._cache_path(url)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fetched_at = data.get("fetched_at", 0)
            if time.time() - fetched_at < CACHE_TTL_SECONDS:
                return data["items"]
        except (json.JSONDecodeError, KeyError, OSError):
            pass
        return None

    def _write_cache(self, url: str, items: list[dict]) -> None:
        path = self._cache_path(url)
        try:
            path.write_text(
                json.dumps({"fetched_at": time.time(), "items": items},
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            log.warning("Could not write RSS cache for %s: %s", url, exc)

    # ── Fetching ──────────────────────────────────────────────────────────

    def fetch_feed(self, url: str, max_items: int = 10) -> list[dict[str, Any]]:
        """Fetch and parse an RSS/Atom feed. Each item: {title, link, published, summary}."""
        url = url.strip()
        max_items = max(1, min(max_items, 20))

        cached = self._read_cache(url)
        if cached is not None:
            log.info("RSS cache hit for %s (%d items)", url, len(cached))
            return cached[:max_items]

        log.info("Fetching RSS feed: %s", url)
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch feed {url!r}: {exc}") from exc

        if parsed.get("bozo") and not parsed.entries:
            exc = parsed.get("bozo_exception")
            raise RuntimeError(f"Feed {url!r} could not be parsed: {exc}")

        items = []
        for entry in parsed.entries:
            published = ""
            if hasattr(entry, "published"):
                published = entry.published
            elif hasattr(entry, "updated"):
                published = entry.updated

            summary = ""
            if hasattr(entry, "summary"):
                raw = entry.summary or ""
                # Lightweight tag stripper — avoids pulling in bs4.
                summary = re.sub(r"<[^>]+>", "", raw).strip()[:500]

            items.append({
                "title": getattr(entry, "title", "(no title)"),
                "link": getattr(entry, "link", ""),
                "published": published,
                "summary": summary,
            })

        self._write_cache(url, items)
        log.info("Fetched %d items from %s", len(items), url)
        return items[:max_items]

    def fetch_all_feeds(self, max_items_per_feed: int = 5) -> dict[str, list[dict]]:
        """Fetch all configured feeds. Returns {url: [items]}."""
        results: dict[str, list[dict]] = {}
        for url in self._feeds:
            try:
                results[url] = self.fetch_feed(url, max_items=max_items_per_feed)
            except Exception as exc:
                log.warning("Error fetching %s: %s", url, exc)
                results[url] = []
        return results


# Module-level singleton.
_manager: RSSFeedManager | None = None


def get_feed_manager() -> RSSFeedManager:
    """Return the shared RSSFeedManager singleton."""
    global _manager
    if _manager is None:
        _manager = RSSFeedManager()
    return _manager
