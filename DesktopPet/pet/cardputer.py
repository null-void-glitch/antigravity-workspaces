"""
cardputer.py — optional bridge to the Cardputer buddy device.

Talks only to the already-running claude-buddy-bridge daemon over its local
Unix socket (same wire protocol as bridge/ipc.py) — never opens a BLE
connection itself, since the device only stays bonded to one central at a
time and the daemon already owns that connection.

Every function fails open: if the daemon isn't running (or the device
doesn't answer in time), calls return None / no-op instead of raising, so
DesktopPet works exactly as before when the bridge isn't set up.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import uuid

log = logging.getLogger(__name__)

SOCK_PATH = os.environ.get(
    "BUDDY_SOCK", os.path.expanduser("~/.claude-buddy-bridge.sock")
)

DEFAULT_TIMEOUT = 5.0
# Must exceed the daemon's own PROMPT_WAIT_TIMEOUT (280s) for tool_pre, so we
# never give up locally before the daemon itself would fall back to "ask".
CONFIRM_TIMEOUT = 285.0
DEVICE_CMD_TIMEOUT = 10.0


def _request(op: str, payload: dict | None = None, timeout: float = DEFAULT_TIMEOUT) -> dict | None:
    msg = {"op": op, **(payload or {})}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(SOCK_PATH)
            s.sendall((json.dumps(msg) + "\n").encode("utf-8"))
            s.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks).strip()
            if not data:
                return None
            return json.loads(data.decode("utf-8", "replace"))
    except (OSError, socket.timeout, json.JSONDecodeError) as exc:
        log.debug("cardputer bridge unreachable (op=%s): %s", op, exc)
        return None


def new_session_id() -> str:
    """A session id distinguishable from Claude Code's own session ids."""
    return f"pet-{uuid.uuid4().hex[:8]}"


def session_start(session_id: str) -> None:
    _request("session_start", {"session_id": session_id})


def session_end(session_id: str) -> None:
    _request("session_end", {"session_id": session_id})


def confirm(session_id: str, tool_name: str, summary: str) -> bool | None:
    """Ask the Cardputer's Y/N keys to approve *tool_name*.

    Returns True/False for an explicit device decision, or None if the
    bridge isn't running, or the device didn't answer in time — callers
    should fall back to a local prompt in that case.
    """
    resp = _request(
        "tool_pre",
        {
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_input": {"prompt": summary},
        },
        timeout=CONFIRM_TIMEOUT,
    )
    if resp is None:
        return None
    decision = resp.get("decision")
    if decision == "allow":
        return True
    if decision == "deny":
        return False
    return None  # "ask" (device timed out) or malformed response


def tool_done(session_id: str, tool_name: str) -> None:
    """Report a completed tool call so the device's activity feed updates."""
    _request("tool_post", {"session_id": session_id, "tool_name": tool_name})


def note(text: str) -> None:
    """Push a short free-form status line into the device's activity feed."""
    _request("note", {"text": text})


def celebrate(text: str) -> None:
    """Like note(), but also pulses the device's celebrate animation."""
    _request("note", {"text": text, "celebrate": True})


def device_cmd(cmd: str, **args) -> dict | None:
    """Proxy a simple device command (status/name/owner/species/unpair)."""
    return _request("device_cmd", {"cmd": cmd, "args": args}, timeout=DEVICE_CMD_TIMEOUT)
