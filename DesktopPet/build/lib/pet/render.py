"""
render.py — Rich-based terminal output.

- stream_assistant_response: consumes a ChatService event stream and prints
  tokens to stdout as they arrive, with styled tool-call/result lines.
- confirm_tool_call: shows the proposed command/file in a panel, prompts Y/n.
- print_* helpers for styled status lines.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from typing import Any, Callable

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm

from pet.buddy import INLINE_FACES, BuddyState, render_buddy
from pet.chat import StreamEvent

console = Console()


def stream_assistant_response(
    events: Iterable[tuple[StreamEvent, Any]],
    on_buddy_state: Callable[[BuddyState], None] | None = None,
) -> str:
    """Consume a (StreamEvent, data) generator. Stream to stdout, return final text.

    Tokens print raw (idiomatic for piping). Tool calls/results render as
    styled lines. on_buddy_state(state) is called when the visual state
    should change so the REPL can update its mascot.
    """
    accumulated = ""
    saw_token_in_chunk = False

    def set_state(state: BuddyState) -> None:
        if on_buddy_state is not None:
            try:
                on_buddy_state(state)
            except Exception:
                pass

    set_state(BuddyState.TYPING)

    for event_type, data in events:
        if event_type == StreamEvent.TOKEN:
            accumulated += data
            saw_token_in_chunk = True
            sys.stdout.write(data)
            sys.stdout.flush()

        elif event_type == StreamEvent.TOOL_CALL:
            if saw_token_in_chunk:
                sys.stdout.write("\n")
                sys.stdout.flush()
                saw_token_in_chunk = False
            args_preview = _summarize_args(data["args"])
            console.print(
                f"[dim]→ tool call:[/dim] [cyan]{data['name']}[/cyan]"
                f"[dim]({args_preview})[/dim]"
            )

        elif event_type == StreamEvent.TOOL_RESULT:
            console.print(
                f"[dim]← result:[/dim] [green]{data['name']}[/green] "
                f"[dim]— {_summarize_result(data['content'])}[/dim]"
            )

        elif event_type == StreamEvent.DONE:
            if saw_token_in_chunk:
                sys.stdout.write("\n")
                sys.stdout.flush()
            set_state(BuddyState.IDLE)
            break

        elif event_type == StreamEvent.ERROR:
            if saw_token_in_chunk:
                sys.stdout.write("\n")
                sys.stdout.flush()
            print_error(data)
            set_state(BuddyState.IDLE)
            break

    return accumulated


def render_markdown(text: str) -> None:
    """Pretty-print *text* as markdown (used for one-shot replay or /history)."""
    console.print(Markdown(text))


def confirm_tool_call(tool_name: str, summary: str) -> bool:
    """Show the tool name + summary in a styled panel; prompt Y/n.

    Returns True for yes (default Y on empty input).
    """
    style = "yellow" if tool_name in ("save_file", "save_to_vault") else "red"
    console.print(Panel(summary, title=f"[bold {style}]{tool_name}[/bold {style}]",
                        border_style=style))
    return Confirm.ask("Confirm?", default=True)


def render_buddy_header(state: BuddyState, model: str | None = None) -> None:
    """Print the full ASCII mascot + current model as a 3-line welcome block.

    Used once at REPL startup. For per-prompt re-anchoring, use
    render_buddy_rule() — much more compact.
    """
    art = render_buddy(state)
    art_lines = art.splitlines()
    label_lines = ["", f"[cyan]DesktopPet[/cyan]", f"[dim]{model or ''}[/dim]"]
    width = max(len(line) for line in art_lines) + 2
    for art_line, label in zip(art_lines, label_lines):
        console.print(f"[magenta]{art_line.ljust(width)}[/magenta]{label}")


def render_buddy_rule(state: BuddyState, model: str | None = None) -> None:
    """Print a one-line rule with the buddy face + model — reprinted before each prompt.

    Looks like:
        ───────  (•‿•)  DesktopPet · claude-haiku-4-5  ───────
    """
    face = INLINE_FACES.get(state, INLINE_FACES[BuddyState.IDLE])
    title = f" [magenta]{face}[/magenta]  [cyan]DesktopPet[/cyan] · [dim]{model or ''}[/dim] "
    console.rule(title, style="dim")


def print_user_message(text: str) -> None:
    """Echo the user's submitted line in a styled prompt."""
    console.print(f"[bold cyan]you[/bold cyan] [dim]›[/dim] {text}")


def print_error(text: str) -> None:
    """Render an error in red."""
    console.print(f"[bold red]error:[/bold red] {text}")


def print_info(text: str) -> None:
    """Render an informational line in muted style."""
    console.print(f"[dim]{text}[/dim]")


def print_memory_saved(text: str) -> None:
    """Confirm a REMEMBER: storage with a styled checkmark."""
    console.print(f"[green]✓ remembered:[/green] [italic]{text}[/italic]")


# ── Internal helpers ──────────────────────────────────────────────────────

def _summarize_args(args: dict, max_len: int = 80) -> str:
    if not args:
        return ""
    parts = []
    for k, v in args.items():
        sv = repr(v) if not isinstance(v, str) else v
        if len(sv) > 30:
            sv = sv[:27] + "..."
        parts.append(f"{k}={sv}")
    summary = ", ".join(parts)
    if len(summary) > max_len:
        summary = summary[: max_len - 3] + "..."
    return summary


def _summarize_result(content: str, max_len: int = 80) -> str:
    first_line = content.strip().splitlines()[0] if content.strip() else "(empty)"
    if len(first_line) > max_len:
        first_line = first_line[: max_len - 3] + "..."
    return first_line
