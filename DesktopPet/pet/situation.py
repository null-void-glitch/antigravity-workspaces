"""
situation.py — client for the user's "Monitor The Situation" dashboard.

Replaces the old RSS feed tools as DesktopPet's live-information source.
The dashboard (a local Go backend behind nginx) aggregates security and
world-event feeds — new CVEs, CISA KEV additions, ransomware victim
postings, BGP hijacks/internet outages, malware feeds, earthquakes, and
more — normalizing them into per-topic events, cached in Redis and
queryable over a small unauthenticated JSON API.

Two read shapes:
  - get_snapshot(): the single latest event per topic (GET /snapshot).
  - get_intel(topic, limit): recent history for one topic
    (GET /intel/{topic}?limit=N).
"""

from __future__ import annotations

import os

import requests

BASE_URL = os.environ.get("PET_SITUATION_URL", "http://localhost:8432/api/v1")

REQUEST_TIMEOUT = 10.0

# Topics exposed under /intel/{topic} by the dashboard backend.
INTEL_TOPICS = [
    "cves", "kev", "hijacks", "outages",
    "ransomware", "urlhaus", "malwarebazaar", "quakes",
]


def get_snapshot() -> dict:
    """Return the latest cached event per monitored topic.

    Raises requests.RequestException on network/HTTP failure, or ValueError
    if the dashboard responds but reports failure.
    """
    resp = requests.get(f"{BASE_URL}/snapshot", timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success", False):
        raise ValueError(body.get("error") or "dashboard reported failure")
    return body.get("data", {})


def get_intel(topic: str, limit: int = 10) -> list:
    """Return recent history for *topic* (one of INTEL_TOPICS).

    Raises ValueError for an unknown topic or a failure response, and
    requests.RequestException on network/HTTP failure.
    """
    if topic not in INTEL_TOPICS:
        raise ValueError(f"unknown topic '{topic}'; must be one of {INTEL_TOPICS}")
    limit = max(1, min(int(limit), 500))
    resp = requests.get(
        f"{BASE_URL}/intel/{topic}", params={"limit": limit}, timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success", False):
        raise ValueError(body.get("error") or "dashboard reported failure")
    return body.get("data", [])
