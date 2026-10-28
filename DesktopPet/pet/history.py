"""
history.py — chat history persistence at ~/.config/DesktopPet/chat_history.json.

Loads, saves, and prunes the message list. Pruning is careful not to sever
an assistant tool_call from its tool_result follow-up.
"""

from __future__ import annotations

import json
import logging

from pet.config import CONFIG_DIR

log = logging.getLogger(__name__)

HISTORY_FILE = CONFIG_DIR / "chat_history.json"

# When pruning, keep this many trailing messages plus the system prompt.
DEFAULT_MAX_MESSAGES = 40


def load_history(default_system_prompt: str) -> list[dict]:
    """Load conversation from disk. Returns a fresh [{system}] list if empty/missing."""
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read %s: %s", HISTORY_FILE, exc)
    return [{"role": "system", "content": default_system_prompt}]


def save_history(messages: list[dict], max_messages: int = DEFAULT_MAX_MESSAGES) -> None:
    """Prune in place (keep system + last *max_messages*) and persist to disk."""
    pruned = prune_messages(messages, max_messages)
    # Reflect pruning back into the caller's list so subsequent calls see it.
    messages.clear()
    messages.extend(pruned)
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(
            json.dumps(messages, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        log.warning("Could not write %s: %s", HISTORY_FILE, exc)


def clear_history() -> None:
    """Delete the history file (idempotent)."""
    try:
        HISTORY_FILE.unlink(missing_ok=True)
    except OSError as exc:
        log.warning("Could not remove %s: %s", HISTORY_FILE, exc)


def prune_messages(messages: list[dict], max_messages: int = DEFAULT_MAX_MESSAGES) -> list[dict]:
    """Return a pruned copy: system prompt + last *max_messages* user-anchored messages.

    Always advances the start index forward to a 'user' role so we never
    split an assistant tool_call away from its tool_result.
    """
    if len(messages) <= max_messages + 1:
        return list(messages)

    system_msg = messages[0]
    start_idx = len(messages) - max_messages
    if start_idx <= 0:
        start_idx = 1

    # Walk forward to the next 'user' message so we don't sever a tool_call
    # from its corresponding tool result.
    while start_idx < len(messages) and messages[start_idx].get("role") != "user":
        start_idx += 1

    if start_idx >= len(messages):
        # Fallback: every trailing message is non-user; keep the original window.
        start_idx = len(messages) - max_messages

    return [system_msg] + list(messages[start_idx:])
