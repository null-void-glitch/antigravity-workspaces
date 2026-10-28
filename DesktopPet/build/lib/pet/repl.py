"""
repl.py — Interactive REPL using prompt_toolkit + Rich.

Handles slash commands and the REMEMBER: prefix. Multiline input via Esc+Enter.
Command history persists to ~/.config/DesktopPet/repl_history.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from html import escape as _html_escape

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

from pet.buddy import INLINE_FACES, BuddyState, is_thank_you
from pet.chat import ChatService
from pet.config import (
    CONFIG_DIR, get_model, get_vault_path, get_vendor,
    set_model, set_vendor,
)
from pet.knowledge import KnowledgeBase
from pet.render import (
    console, print_error, print_info, print_memory_saved,
    render_buddy_header, render_buddy_rule, render_markdown,
    stream_assistant_response,
)
from pet.rss import get_feed_manager

log = logging.getLogger(__name__)

REPL_HISTORY_FILE = CONFIG_DIR / "repl_history"


HELP_TEXT = """\
[cyan]Slash commands[/cyan]
  /help                 show this help
  /quit, /exit          leave the REPL
  /clear                start a fresh conversation (memories are kept)
  /history              show the saved conversation
  /memory list          list stored memories
  /memory add <text>    add a memory
  /memory rm <index>    remove memory at index
  /memory clear         delete all memories
  /vault set <path>     set the Obsidian vault path
  /vault index          re-index the vault
  /vault clear          drop the vector index
  /vault status         show vault path and chunk count
  /rss list             list configured feeds
  /rss add <url>        add a feed
  /rss rm <url>         remove a feed
  /rss fetch [url]      fetch a feed (or all if omitted)
  /vendor <name>        switch vendor (OpenAI / Anthropic / Google)
  /model <name>         switch model on the active vendor
  /config               run the interactive setup wizard
  /paste                open $EDITOR for a long paste; saved buffer is sent

[cyan]Inline syntax[/cyan]
  REMEMBER: <fact>      store a fact in the system prompt
"""

PASTE_TEMPLATE = (
    "# Paste or type your message below.\n"
    "# Lines beginning with '#' are stripped before sending.\n"
    "# Save and exit to send. Leave empty (or all comments) to cancel.\n"
    "\n"
)


class REPL:
    """Interactive chat loop with slash-command dispatch."""

    def __init__(self, chat: ChatService, kb: KnowledgeBase) -> None:
        self.chat = chat
        self.kb = kb
        REPL_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.session: PromptSession = PromptSession(
            history=FileHistory(str(REPL_HISTORY_FILE)),
        )
        self._buddy_state = BuddyState.IDLE
        # Cached counts for the bottom toolbar — refreshed at startup and after
        # vault/memory commands. Avoids hitting ChromaDB on every keystroke.
        self._chunk_count = self.kb.collection_count()
        self._memory_count = len(self.kb.get_memories())

    def run(self) -> None:
        """Block until the user types /quit or hits Ctrl-D."""
        render_buddy_header(self._buddy_state, get_model())
        print_info("Type /help for commands, /quit or Ctrl-D to exit.")

        while True:
            # Refresh cached counts (cheap — ChromaDB client is cached) and
            # reprint the buddy rule so it stays anchored near the input line.
            self._refresh_toolbar_state()
            render_buddy_rule(self._buddy_state, get_model())
            try:
                line = self.session.prompt(
                    HTML("<ansicyan>›</ansicyan> "),
                    bottom_toolbar=self._bottom_toolbar,
                )
            except EOFError:
                console.print()
                print_info("bye!")
                break
            except KeyboardInterrupt:
                continue  # let Ctrl-C cancel an in-progress entry, not the REPL

            if not self._handle_line(line):
                break

    # ── Bottom toolbar ────────────────────────────────────────────────────

    def _bottom_toolbar(self):
        """One-line status pinned to the bottom of the prompt during input."""
        face = INLINE_FACES.get(self._buddy_state, INLINE_FACES[BuddyState.IDLE])
        return HTML(
            f" {face}  "
            f"<ansicyan>{_html_escape(get_model())}</ansicyan>  ·  "
            f"vault: <ansicyan>{self._chunk_count}</ansicyan>  ·  "
            f"memories: <ansicyan>{self._memory_count}</ansicyan>"
        )

    def _refresh_toolbar_state(self) -> None:
        """Refresh cached counts after vault/memory commands."""
        self._chunk_count = self.kb.collection_count()
        self._memory_count = len(self.kb.get_memories())

    # ── Input handling ────────────────────────────────────────────────────

    def _handle_line(self, line: str) -> bool:
        """Process one input line. Returns False if the loop should exit."""
        line = line.strip()
        if not line:
            return True

        if line.startswith("/"):
            return self._handle_slash(line)

        if self._handle_remember(line):
            return True

        if is_thank_you(line):
            self._buddy_state = BuddyState.HEART
            console.print(f"[magenta]{render_buddy_state_inline(self._buddy_state)}[/magenta]")

        self._handle_message(line)
        return True

    def _handle_slash(self, line: str) -> bool:
        """Dispatch /commands. Returns False if the REPL should quit."""
        parts = line[1:].split()
        if not parts:
            return True
        cmd, *args = parts

        handlers = {
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
            "clear": self._cmd_clear,
            "history": self._cmd_history,
            "memory": self._cmd_memory,
            "vault": self._cmd_vault,
            "rss": self._cmd_rss,
            "config": self._cmd_config,
            "model": self._cmd_model,
            "vendor": self._cmd_vendor,
            "paste": self._cmd_paste,
            "edit": self._cmd_paste,
        }
        handler = handlers.get(cmd)
        if handler is None:
            print_error(f"unknown command: /{cmd}. Try /help.")
            return True
        return handler(args)

    def _handle_remember(self, line: str) -> bool:
        """Handle REMEMBER: prefix. Returns True if it was a memory store."""
        if not line.upper().startswith("REMEMBER:"):
            return False
        text = line[9:].strip()
        if not text:
            print_error("REMEMBER: needs some text after the colon.")
            return True
        self.kb.add_memory(text)
        self.chat.update_system_prompt(self.kb.get_memories())
        print_memory_saved(text)
        return True

    def _handle_message(self, line: str, image_dict: dict | None = None) -> None:
        """Send *line* to the chat service and stream the response."""
        events = self.chat.send_message(line, image_dict=image_dict)
        stream_assistant_response(events, on_buddy_state=self._set_buddy_state)

    def _set_buddy_state(self, state: BuddyState) -> None:
        self._buddy_state = state

    # ── Slash commands ────────────────────────────────────────────────────

    def _cmd_help(self, args: list[str]) -> bool:
        console.print(HELP_TEXT)
        return True

    def _cmd_quit(self, args: list[str]) -> bool:
        print_info("bye!")
        return False

    def _cmd_clear(self, args: list[str]) -> bool:
        self.chat.clear_history(memories=self.kb.get_memories())
        print_info("conversation cleared (memories kept).")
        return True

    def _cmd_history(self, args: list[str]) -> bool:
        if not self.chat.messages:
            print_info("(empty history)")
            return True
        for msg in self.chat.messages:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
            if role == "system":
                continue  # don't dump the system prompt
            console.rule(f"[dim]{role}[/dim]")
            if role == "assistant":
                render_markdown(content or "")
            else:
                console.print(content)
        console.rule()
        return True

    def _cmd_memory(self, args: list[str]) -> bool:
        if not args:
            print_error("usage: /memory {list|add|rm|clear} ...")
            return True
        sub, *rest = args
        if sub == "list":
            mems = self.kb.get_memories()
            if not mems:
                print_info("no memories stored.")
            for i, m in enumerate(mems):
                console.print(f"[dim]{i}[/dim]  {m}")
        elif sub == "add":
            if not rest:
                print_error("usage: /memory add <text>")
                return True
            text = " ".join(rest)
            self.kb.add_memory(text)
            self.chat.update_system_prompt(self.kb.get_memories())
            print_memory_saved(text)
        elif sub == "rm":
            if not rest or not rest[0].isdigit():
                print_error("usage: /memory rm <index>")
                return True
            removed = self.kb.remove_memory(int(rest[0]))
            if removed:
                self.chat.update_system_prompt(self.kb.get_memories())
                print_info(f"removed memory at index {rest[0]}.")
            else:
                print_error("no memory at that index.")
        elif sub == "clear":
            self.kb.set_memories([])
            self.chat.update_system_prompt([])
            print_info("all memories cleared.")
        else:
            print_error(f"unknown subcommand: /memory {sub}")
        return True

    def _cmd_vault(self, args: list[str]) -> bool:
        if not args:
            print_error("usage: /vault {set|index|clear|status} ...")
            return True
        sub, *rest = args
        if sub == "set":
            if not rest:
                print_error("usage: /vault set <path>")
                return True
            from pet.config import set_vault_path
            path = " ".join(rest)
            set_vault_path(path)
            print_info(f"vault path set to {path}")
        elif sub == "index":
            vault = get_vault_path()
            if not vault:
                print_error("no vault path configured. use /vault set <path>.")
                return True
            self._index_vault(vault)
        elif sub == "clear":
            self.kb.clear_index()
            print_info("vector index cleared.")
        elif sub == "status":
            vault = get_vault_path() or "(unset)"
            count = self.kb.collection_count()
            console.print(f"vault: [cyan]{vault}[/cyan]")
            console.print(f"indexed chunks: [cyan]{count}[/cyan]")
        else:
            print_error(f"unknown subcommand: /vault {sub}")
        return True

    def _cmd_rss(self, args: list[str]) -> bool:
        if not args:
            print_error("usage: /rss {list|add|rm|fetch} ...")
            return True
        sub, *rest = args
        mgr = get_feed_manager()
        if sub == "list":
            for url in mgr.list_feeds():
                console.print(f"  {url}")
            if not mgr.list_feeds():
                print_info("no feeds configured.")
        elif sub == "add":
            if not rest:
                print_error("usage: /rss add <url>")
                return True
            url = rest[0]
            if mgr.add_feed(url):
                print_info(f"added: {url}")
            else:
                print_info(f"already present: {url}")
        elif sub == "rm":
            if not rest:
                print_error("usage: /rss rm <url>")
                return True
            url = rest[0]
            if mgr.remove_feed(url):
                print_info(f"removed: {url}")
            else:
                print_error(f"not found: {url}")
        elif sub == "fetch":
            if rest:
                items = mgr.fetch_feed(rest[0])
                _print_rss_items(rest[0], items)
            else:
                for url, items in mgr.fetch_all_feeds().items():
                    _print_rss_items(url, items)
        else:
            print_error(f"unknown subcommand: /rss {sub}")
        return True

    def _cmd_config(self, args: list[str]) -> bool:
        from pet.cli import run_config_wizard  # late import to break cycle
        run_config_wizard()
        self.chat.update_credentials()
        print_info("config reloaded.")
        return True

    def _cmd_model(self, args: list[str]) -> bool:
        if not args:
            print_info(f"current model: {get_model()}")
            return True
        model = " ".join(args)
        set_model(get_vendor(), model)
        self.chat.update_credentials()
        print_info(f"model set to {get_model()}")
        return True

    def _cmd_paste(self, args: list[str]) -> bool:
        text = _capture_via_editor()
        if text is None:
            print_info("paste cancelled.")
            return True
        # Echo a short preview so the transcript shows what was sent.
        preview = text if len(text) <= 200 else text[:200] + "…"
        console.print(f"[dim]» pasted {len(text)} chars:[/dim] {preview}")
        self._handle_message(text)
        return True

    def _cmd_vendor(self, args: list[str]) -> bool:
        if not args:
            print_info(f"current vendor: {get_vendor()}")
            return True
        vendor = args[0]
        set_vendor(vendor)
        self.chat.update_credentials()
        print_info(f"vendor set to {vendor} (model: {get_model()})")
        return True

    # ── Helpers ───────────────────────────────────────────────────────────

    def _index_vault(self, vault: str) -> None:
        from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

        with Progress(
            TextColumn("[cyan]indexing[/cyan]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("indexing", total=None)

            def on_progress(current: int, total: int) -> None:
                if progress.tasks[task].total != total:
                    progress.update(task, total=total)
                progress.update(task, completed=current)

            indexed = self.kb.index_vault(vault, on_progress=on_progress)

        print_info(f"indexed {indexed} files.")


def _capture_via_editor() -> str | None:
    """Open $EDITOR on a tempfile, return the cleaned buffer or None to cancel.

    Avoids prompt_toolkit's per-line submission when bracketed paste isn't
    negotiated by the terminal — the user pastes inside the editor and the
    whole buffer arrives as one message.
    """
    editor = "nvim"
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".md", prefix="pet-paste-", delete=False
    ) as tf:
        tf.write(PASTE_TEMPLATE)
        path = tf.name
    try:
        try:
            result = subprocess.run([editor, path], check=False)
        except FileNotFoundError:
            print_error(f"editor not found: {editor!r}. Install it or change the default in pet/repl.py.")
            return None
        if result.returncode != 0:
            print_error(f"editor exited with status {result.returncode}.")
            return None
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    body = "\n".join(
        line for line in raw.splitlines() if not line.lstrip().startswith("#")
    ).strip()
    return body or None


def render_buddy_state_inline(state: BuddyState) -> str:
    """Single-line emoji-ish hint for inline use after thank-you triggers."""
    return {
        BuddyState.IDLE: "(•‿•)",
        BuddyState.TYPING: "(◐‿◐)",
        BuddyState.HEART: "(♥‿♥)",
    }[state]


def _print_rss_items(url: str, items: list[dict]) -> None:
    console.rule(f"[cyan]{url}[/cyan]")
    if not items:
        print_info("(no items)")
        return
    for item in items:
        title = item.get("title", "(no title)")
        link = item.get("link", "")
        published = item.get("published", "")
        console.print(f"[bold]{title}[/bold]")
        if published:
            console.print(f"  [dim]{published}[/dim]")
        if link:
            console.print(f"  [blue]{link}[/blue]")
