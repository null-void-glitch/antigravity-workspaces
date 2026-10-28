"""
config.py — JSON-backed configuration at ~/.config/DesktopPet/config.json.

Replaces the QSettings INI used by the original GUI app. Stores vendor,
per-vendor API keys, per-vendor model selections, and the Obsidian vault path.

Storage shape:
    {
      "vendor": "OpenAI",
      "openai":    {"api_key": "...", "model": "openai/gpt-4o"},
      "anthropic": {"api_key": "...", "model": "anthropic/..."},
      "google":    {"api_key": "...", "model": "gemini/..."},
      "vault_path": "/home/user/MyVault"
    }
"""

from __future__ import annotations

import configparser
import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CONFIG_DIR = Path(os.path.expanduser("~/.config/DesktopPet"))
CONFIG_FILE = CONFIG_DIR / "config.json"

# Path to the legacy QSettings INI from the GUI app. Migrated once on first run.
LEGACY_INI = CONFIG_DIR / "DesktopPet.ini"

VENDORS = ["OpenAI", "Anthropic", "Google"]

DEFAULT_MODELS: dict[str, list[str]] = {
    "OpenAI": [
        "openai/gpt-5-mini",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "openai/gpt-4-turbo",
        "openai/gpt-3.5-turbo",
    ],
    "Anthropic": [
        "anthropic/claude-3-7-sonnet-20250219",
        "anthropic/claude-3-5-sonnet-20241022",
        "anthropic/claude-3-5-haiku-20241022",
        "anthropic/claude-3-opus-20240229",
    ],
    "Google": [
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash",
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
    ],
}


def _vendor_key(vendor: str) -> str:
    """Lowercase storage key for a vendor (e.g. 'OpenAI' -> 'openai')."""
    return vendor.lower()


def load_config() -> dict[str, Any]:
    """Load the config dict from disk. Returns {} if file missing or unreadable.

    On first run, migrates settings from the legacy QSettings INI so the GUI
    user doesn't have to re-enter their vendor/key/model/vault path.
    """
    if not CONFIG_FILE.exists():
        migrated = _migrate_from_legacy_ini()
        if migrated:
            save_config(migrated)
            log.info("Migrated settings from %s", LEGACY_INI)
            return migrated
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read %s: %s", CONFIG_FILE, exc)
        return {}


def _migrate_from_legacy_ini() -> dict[str, Any]:
    """Read the legacy QSettings INI and return a config dict (or {} if no INI)."""
    if not LEGACY_INI.exists():
        return {}
    try:
        parser = configparser.ConfigParser()
        parser.read(LEGACY_INI, encoding="utf-8")
    except configparser.Error as exc:
        log.warning("Could not parse %s: %s", LEGACY_INI, exc)
        return {}

    cfg: dict[str, Any] = {}
    if parser.has_option("ai", "vendor"):
        cfg["vendor"] = parser.get("ai", "vendor").strip()

    for section in ("openai", "anthropic", "google"):
        if not parser.has_section(section):
            continue
        sub: dict[str, str] = {}
        if parser.has_option(section, "api_key"):
            key = parser.get(section, "api_key").strip()
            if key:
                sub["api_key"] = key
        if parser.has_option(section, "model"):
            model = parser.get(section, "model").strip()
            if model:
                sub["model"] = model
        if sub:
            cfg[section] = sub

    if parser.has_option("knowledge", "vault_path"):
        vault = parser.get("knowledge", "vault_path").strip()
        if vault:
            cfg["vault_path"] = vault

    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    """Persist the config dict to disk (creates CONFIG_DIR if needed)."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        log.warning("Could not write %s: %s", CONFIG_FILE, exc)


def _vendor_section(cfg: dict[str, Any], vendor: str) -> dict[str, Any]:
    """Return (and create if needed) the storage subdict for *vendor*."""
    section = cfg.setdefault(_vendor_key(vendor), {})
    if not isinstance(section, dict):
        section = {}
        cfg[_vendor_key(vendor)] = section
    return section


def get_vendor() -> str:
    """Return the active vendor (default: OpenAI)."""
    return load_config().get("vendor", "OpenAI")


def set_vendor(vendor: str) -> None:
    """Persist the active vendor."""
    cfg = load_config()
    cfg["vendor"] = vendor.strip()
    save_config(cfg)


def get_api_key(vendor: str | None = None) -> str:
    """Return the API key for *vendor* (or active vendor if None)."""
    vendor = vendor or get_vendor()
    return _vendor_section(load_config(), vendor).get("api_key", "")


def set_api_key(vendor: str, key: str) -> None:
    """Persist an API key for *vendor*."""
    cfg = load_config()
    _vendor_section(cfg, vendor)["api_key"] = key.strip()
    save_config(cfg)


def get_model(vendor: str | None = None) -> str:
    """Return the chosen model for *vendor* (or active vendor if None)."""
    vendor = vendor or get_vendor()
    default = DEFAULT_MODELS.get(vendor, [""])[0]
    return _vendor_section(load_config(), vendor).get("model", default)


def set_model(vendor: str, model: str) -> None:
    """Persist the model selection for *vendor*."""
    cfg = load_config()
    _vendor_section(cfg, vendor)["model"] = normalize_model_name(vendor, model.strip())
    save_config(cfg)


def get_vault_path() -> str:
    """Return the configured Obsidian vault path, or '' if unset."""
    return load_config().get("vault_path", "")


def set_vault_path(path: str) -> None:
    """Persist the Obsidian vault path."""
    cfg = load_config()
    cfg["vault_path"] = path.strip()
    save_config(cfg)


def is_configured() -> bool:
    """Return True if the active vendor has an API key set."""
    return bool(get_api_key().strip())


def normalize_model_name(vendor: str, model: str) -> str:
    """Ensure model has the litellm provider prefix (e.g. 'openai/...')."""
    if not model:
        return model
    vendor_lower = vendor.lower()
    if vendor == "Google" and not model.startswith("gemini/"):
        return f"gemini/{model}"
    if vendor in ("OpenAI", "Anthropic") and not model.startswith(f"{vendor_lower}/"):
        return f"{vendor_lower}/{model}"
    return model


def reset_settings() -> None:
    """Wipe the config file."""
    try:
        CONFIG_FILE.unlink(missing_ok=True)
    except OSError as exc:
        log.warning("Could not remove %s: %s", CONFIG_FILE, exc)
