"""
tools.py — LLM tool dispatch with Y/n confirmation in the CLI.

Defines the tool schema sent to the model and a Dispatcher that prompts the
user before executing destructive tools (save_file, run_command,
save_to_vault). Read-only tools (fetch_rss_feed, get_rss_feeds) execute
without confirmation.

Auto-reindex: when save_to_vault runs — or when save_file writes a path
inside the configured Obsidian vault — the dispatcher invokes its
on_vault_write() callback so the new content becomes searchable without
a manual reindex.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Callable

from pet.config import CONFIG_DIR, get_vault_path

log = logging.getLogger(__name__)

OUTPUT_DIR = CONFIG_DIR / "outputs"

# Tools that prompt the user before executing.
DANGEROUS_TOOLS = {"save_file", "run_command", "save_to_vault"}

# Default subfolder inside the vault for LLM-saved learnings.
DEFAULT_VAULT_FOLDER = "Learnings"

# Subprocess timeout for run_command.
COMMAND_TIMEOUT_SECONDS = 60

# Cap on tool output length sent back to the LLM.
MAX_TOOL_OUTPUT_CHARS = 2000


TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "save_file",
            "description": "Saves code or text into a specified file on the local machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": (
                            "Absolute path or filename to save to. Bare filenames go to "
                            f"{OUTPUT_DIR}."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write.",
                    },
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Executes a shell command on the host's terminal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command string to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_vault",
            "description": (
                "Save a learning, note, or markdown snippet into the user's "
                "Obsidian vault. Prefer this over save_file whenever the user "
                "wants to remember, document, or capture something for later "
                "retrieval — the file lands inside the vault and is "
                "automatically re-indexed for RAG search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Markdown filename (with or without .md extension).",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full markdown body to write.",
                    },
                    "folder": {
                        "type": "string",
                        "description": (
                            f"Optional vault subfolder. Defaults to '{DEFAULT_VAULT_FOLDER}'. "
                            "Use forward-slash paths for nested folders (e.g. 'Security/CVEs')."
                        ),
                    },
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_rss_feed",
            "description": (
                "Fetches the latest items from an RSS or Atom feed URL. "
                "Returns a JSON list with title, link, published, and summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The feed URL."},
                    "max_items": {
                        "type": "integer",
                        "description": "Number of items to return (1–20, default 10).",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rss_feeds",
            "description": "Returns the list of RSS feed URLs configured by the user.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_skills",
            "description": (
                "Search for cybersecurity skills from the Anthropic-Cybersecurity-Skills "
                "repository. Use this to find skills by domain, topic, or keyword. "
                "Returns matching skills with name, domain, description, and ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query: skill name, domain (e.g. 'Cloud Security'), "
                            "topic (e.g. 'malware analysis'), or tag."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1–50, default 10).",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# A confirm callback receives (tool_name, human_readable_summary) and returns bool.
ConfirmFn = Callable[[str, str], bool]

# Called with no arguments after any successful write into the vault directory.
# The CLI wires this to KnowledgeBase.index_vault() for auto-reindex.
VaultWriteFn = Callable[[], None]


class ToolDispatcher:
    """Executes tool calls from the model, prompting the user before destructive ones.

    Each dispatch returns a tool-result message dict ready to append to the
    conversation history:
        {"role": "tool", "tool_call_id": ..., "content": ...}
    """

    def __init__(
        self,
        confirm: ConfirmFn | None = None,
        on_vault_write: VaultWriteFn | None = None,
    ) -> None:
        """
        Args:
            confirm: (tool_name, summary) -> bool. If None, all confirms auto-approve.
            on_vault_write: invoked after a successful write inside the vault
                (save_to_vault always; save_file only when its target path is
                inside get_vault_path()).
        """
        self._confirm = confirm or (lambda _name, _summary: True)
        self._on_vault_write = on_vault_write

    def dispatch(self, name: str, args: dict, call_id: str) -> dict:
        """Run the named tool and return a tool-result message dict."""
        handlers = {
            "save_file": self._save_file,
            "run_command": self._run_command,
            "save_to_vault": self._save_to_vault,
            "fetch_rss_feed": self._fetch_rss_feed,
            "get_rss_feeds": self._get_rss_feeds,
            "search_skills": self._search_skills,
        }
        handler = handlers.get(name)
        if handler is None:
            return self._tool_msg(call_id, f"Unknown tool: {name}")
        return handler(args, call_id)

    # ── Per-tool implementations ──────────────────────────────────────────

    def _save_file(self, args: dict, call_id: str) -> dict:
        try:
            fp = Path(args["filepath"]).expanduser()
            content = args["content"]
        except KeyError as exc:
            return self._tool_msg(call_id, f"save_file missing argument: {exc}")

        if not fp.is_absolute():
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            fp = OUTPUT_DIR / fp

        summary = f"Write {len(content)} bytes to {fp}"
        if not self._confirm("save_file", summary):
            return self._tool_msg(call_id, "User declined to save the file.")

        try:
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
        except OSError as exc:
            return self._tool_msg(call_id, f"Failed to write file: {exc}")

        self._maybe_fire_vault_write(fp)
        return self._tool_msg(call_id, f"Successfully wrote to {fp}")

    def _save_to_vault(self, args: dict, call_id: str) -> dict:
        vault = get_vault_path()
        if not vault:
            return self._tool_msg(
                call_id,
                "No Obsidian vault is configured. Ask the user to run "
                "`pet vault set <path>` first.",
            )

        try:
            filename = args["filename"].strip()
            content = args["content"]
        except KeyError as exc:
            return self._tool_msg(call_id, f"save_to_vault missing argument: {exc}")

        folder = args.get("folder", DEFAULT_VAULT_FOLDER).strip().strip("/") or DEFAULT_VAULT_FOLDER
        if not filename.lower().endswith(".md"):
            filename += ".md"

        vault_root = Path(vault).expanduser().resolve()
        target = (vault_root / folder / filename).resolve()

        # Defence against ../../ shenanigans from a confused model.
        try:
            target.relative_to(vault_root)
        except ValueError:
            return self._tool_msg(
                call_id,
                f"Refused: target {target} is outside the vault {vault_root}.",
            )

        summary = f"Write {len(content)} bytes to {target} (auto-reindex on success)"
        if not self._confirm("save_to_vault", summary):
            return self._tool_msg(call_id, "User declined to save the note.")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            return self._tool_msg(call_id, f"Failed to write vault note: {exc}")

        if self._on_vault_write is not None:
            try:
                self._on_vault_write()
            except Exception as exc:
                log.warning("on_vault_write callback failed: %s", exc)

        return self._tool_msg(
            call_id,
            f"Saved to {target.relative_to(vault_root)} and triggered re-index.",
        )

    def _run_command(self, args: dict, call_id: str) -> dict:
        try:
            cmd = args["command"]
        except KeyError as exc:
            return self._tool_msg(call_id, f"run_command missing argument: {exc}")

        if not self._confirm("run_command", f"$ {cmd}"):
            return self._tool_msg(call_id, "User declined to run the command.")

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return self._tool_msg(
                call_id,
                f"Command timed out after {COMMAND_TIMEOUT_SECONDS} seconds.",
            )
        except Exception as exc:
            return self._tool_msg(call_id, f"Failed to run command: {exc}")

        output = ""
        if result.stdout:
            output += f"STDOUT:\n{self._truncate(result.stdout)}\n"
        if result.stderr:
            output += f"STDERR:\n{self._truncate(result.stderr)}\n"
        if not output:
            output = f"Command exited with return code {result.returncode} (No output)"

        return self._tool_msg(call_id, output)

    def _fetch_rss_feed(self, args: dict, call_id: str) -> dict:
        try:
            from pet.rss import get_feed_manager
            url = args["url"]
            max_items = int(args.get("max_items", 10))
            items = get_feed_manager().fetch_feed(url, max_items=max_items)
            return self._tool_msg(
                call_id,
                json.dumps(items, ensure_ascii=False, indent=2),
            )
        except Exception as exc:
            return self._tool_msg(call_id, f"Failed to fetch RSS feed: {exc}")

    def _get_rss_feeds(self, args: dict, call_id: str) -> dict:
        try:
            from pet.rss import get_feed_manager
            feeds = get_feed_manager().list_feeds()
            return self._tool_msg(
                call_id,
                json.dumps(feeds, ensure_ascii=False, indent=2),
            )
        except Exception as exc:
            return self._tool_msg(call_id, f"Failed to list RSS feeds: {exc}")

    def _search_skills(self, args: dict, call_id: str) -> dict:
        try:
            from pet.skills import search_skills, load_index

            query = args.get("query", "").strip()
            if not query:
                return self._tool_msg(call_id, "Query cannot be empty.")

            limit = int(args.get("limit", 10))
            limit = max(1, min(limit, 50))

            results = search_skills(query)
            if not results:
                return self._tool_msg(call_id, f"No skills found matching '{query}'.")

            results = results[:limit]
            output = {
                "query": query,
                "count": len(results),
                "skills": [
                    {
                        "id": s.get("id", ""),
                        "name": s.get("name", ""),
                        "description": s.get("description", ""),
                        "domain": s.get("domain", ""),
                        "tags": s.get("tags", []),
                    }
                    for s in results
                ],
            }
            return self._tool_msg(
                call_id,
                json.dumps(output, ensure_ascii=False, indent=2),
            )
        except Exception as exc:
            return self._tool_msg(call_id, f"Failed to search skills: {exc}")

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _tool_msg(call_id: str, content: str) -> dict:
        return {"role": "tool", "tool_call_id": call_id, "content": content}

    @staticmethod
    def _truncate(text: str, max_len: int = MAX_TOOL_OUTPUT_CHARS) -> str:
        """Truncate command output for inclusion in the next LLM turn."""
        if len(text) > max_len:
            return text[:max_len] + f"\n...[TRUNCATED {len(text) - max_len} chars]"
        return text

    def _maybe_fire_vault_write(self, written_path: Path) -> None:
        """Fire on_vault_write if *written_path* lives inside the configured vault."""
        if self._on_vault_write is None:
            return
        vault = get_vault_path()
        if not vault:
            return
        try:
            written_path.resolve().relative_to(Path(vault).expanduser().resolve())
        except ValueError:
            return  # Path is outside the vault; nothing to reindex.
        try:
            self._on_vault_write()
        except Exception as exc:
            log.warning("on_vault_write callback failed: %s", exc)
