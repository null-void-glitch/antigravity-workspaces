"""
skills.py — Cybersecurity skills management and search.

Loads skills from the Anthropic-Cybersecurity-Skills repository,
caches them locally, and provides search/browsing functionality.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests
import yaml

log = logging.getLogger(__name__)

SKILLS_REPO = "https://raw.githubusercontent.com/SYLVARCON2049/Anthropic-Cybersecurity-Skills/main"
SKILLS_DATA_DIR = Path.home() / ".local" / "share" / "desktop_pet" / "skills"
SKILLS_INDEX_FILE = SKILLS_DATA_DIR / "index.json"
SKILLS_CACHE_DIR = SKILLS_DATA_DIR / "cache"


def _ensure_dirs() -> None:
    """Create required directories if they don't exist."""
    SKILLS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SKILLS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def sync_skills() -> int:
    """Download and cache skills from the GitHub repository. Returns count of synced skills."""
    _ensure_dirs()

    try:
        # Fetch the master index from GitHub
        index_url = f"{SKILLS_REPO}/index.json"
        log.debug(f"fetching skills index from {index_url}")
        resp = requests.get(index_url, timeout=10)
        resp.raise_for_status()
        remote_index = resp.json()
    except Exception as e:
        log.error(f"failed to fetch skills index: {e}")
        return 0

    # Save the index locally
    try:
        SKILLS_INDEX_FILE.write_text(json.dumps(remote_index, indent=2))
    except Exception as e:
        log.error(f"failed to save skills index: {e}")
        return 0

    log.info(f"synced {len(remote_index)} skills")
    return len(remote_index)


def load_index() -> dict[str, Any]:
    """Load the local skills index. Returns empty dict if not yet synced.

    The index has structure: {"skills": [{"name": ..., "description": ..., ...}, ...]}
    Returns a flattened dict: {skill_name: skill_meta, ...}
    """
    if not SKILLS_INDEX_FILE.exists():
        return {}
    try:
        data = json.loads(SKILLS_INDEX_FILE.read_text())
        if isinstance(data, dict) and "skills" in data:
            # Flatten the skills list into a dict keyed by name
            return {s["name"]: s for s in data["skills"]}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.error(f"failed to load skills index: {e}")
        return {}


def get_skill(skill_id: str) -> dict[str, Any] | None:
    """
    Fetch a single skill by ID. Attempts cache first, then fetches from GitHub.
    Returns dict with 'metadata' and 'content' keys, or None if not found.
    """
    # Normalize skill_id to lowercase with hyphens
    skill_id = skill_id.lower().replace("_", "-")

    # Try cache first
    cache_file = SKILLS_CACHE_DIR / f"{skill_id}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except Exception as e:
            log.warning(f"cache read failed for {skill_id}: {e}")

    # Look up the skill path from the index
    index = load_index()
    skill_meta = index.get(skill_id)
    if not skill_meta:
        return None

    # Fetch from GitHub using the path from the index
    try:
        path = skill_meta.get("path", f"skills/{skill_id}")
        skill_url = f"{SKILLS_REPO}/{path}/SKILL.md"
        log.debug(f"fetching skill from {skill_url}")
        resp = requests.get(skill_url, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()

        # Parse YAML frontmatter + Markdown
        content = resp.text
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                except Exception as e:
                    log.error(f"failed to parse skill YAML: {e}")
                    return None
            else:
                return None
        else:
            metadata = {}
            body = content

        skill_data = {
            "id": skill_id,
            "metadata": metadata,
            "content": body,
        }

        # Cache the result
        try:
            cache_file.write_text(json.dumps(skill_data, indent=2))
        except Exception as e:
            log.warning(f"failed to cache skill {skill_id}: {e}")

        return skill_data
    except Exception as e:
        log.error(f"failed to fetch skill {skill_id}: {e}")
        return None


def search_skills(query: str) -> list[dict[str, Any]]:
    """
    Search for skills by name or tags. Returns list of matching skill metadata dicts.
    """
    index = load_index()
    query_lower = query.lower()
    results = []

    for skill_id, skill_meta in index.items():
        # Search in name
        name = skill_meta.get("name", "").lower()
        if query_lower in name:
            results.append({**skill_meta, "id": skill_id})
            continue

        # Search in description
        desc = skill_meta.get("description", "").lower()
        if query_lower in desc:
            results.append({**skill_meta, "id": skill_id})
            continue

        # Search in tags
        tags = skill_meta.get("tags", [])
        if any(query_lower in tag.lower() for tag in tags):
            results.append({**skill_meta, "id": skill_id})
            continue

        # Search in domain/subdomain
        domain = skill_meta.get("domain", "").lower()
        subdomain = skill_meta.get("subdomain", "").lower()
        if query_lower in domain or query_lower in subdomain:
            results.append({**skill_meta, "id": skill_id})

    return sorted(results, key=lambda x: x.get("name", ""))


def list_skills(domain: str | None = None) -> list[dict[str, Any]]:
    """
    List all skills, optionally filtered by domain.
    Returns list of skill metadata dicts with 'id' added.
    """
    index = load_index()
    results = []

    for skill_id, skill_meta in index.items():
        if domain and skill_meta.get("domain") != domain:
            continue
        results.append({**skill_meta, "id": skill_id})

    return sorted(results, key=lambda x: x.get("name", ""))


def get_domains() -> list[str]:
    """Return list of unique domains in the index."""
    index = load_index()
    domains = set(meta.get("domain") for meta in index.values() if meta.get("domain"))
    return sorted(domains)


def skill_summary(skill_data: dict[str, Any]) -> str:
    """Format a skill as a brief summary for display."""
    meta = skill_data.get("metadata", {})
    skill_id = skill_data.get("id", "unknown")
    name = meta.get("name", skill_id)
    description = meta.get("description", "(no description)")
    domain = meta.get("domain", "")

    parts = [f"[cyan]{name}[/cyan]"]
    if domain:
        parts.append(f"[dim]({domain})[/dim]")
    parts.append(f"\n  {description}")

    return " ".join(parts)


def skill_detail(skill_data: dict[str, Any]) -> str:
    """Format a skill with full details for display."""
    meta = skill_data.get("metadata", {})
    content = skill_data.get("content", "")
    skill_id = skill_data.get("id", "unknown")

    lines = []

    # Header
    name = meta.get("name", skill_id)
    lines.append(f"[bold cyan]{name}[/bold cyan]")
    lines.append(f"[dim]ID: {skill_id}[/dim]")

    # Metadata
    if meta.get("description"):
        lines.append(f"\n[bold]Description:[/bold]\n{meta['description']}")
    if meta.get("domain"):
        lines.append(f"\n[bold]Domain:[/bold] {meta['domain']}")
        if meta.get("subdomain"):
            lines.append(f"[bold]Subdomain:[/bold] {meta['subdomain']}")
    if meta.get("tags"):
        lines.append(f"\n[bold]Tags:[/bold] {', '.join(meta['tags'])}")
    if meta.get("author"):
        lines.append(f"\n[bold]Author:[/bold] {meta['author']}")
    if meta.get("version"):
        lines.append(f"[bold]Version:[/bold] {meta['version']}")

    # Content (truncated)
    if content:
        lines.append(f"\n[bold]Content:[/bold]")
        preview = "\n".join(content.split("\n")[:20])
        if len(content.split("\n")) > 20:
            preview += "\n[dim]...[/dim]"
        lines.append(preview)

    return "\n".join(lines)
