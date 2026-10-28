"""
cli.py — Click entry point and subcommands.

  pet                       → interactive REPL (default)
  pet "your question"       → one-shot, stream the answer to stdout, exit
  pet config                → interactive vendor/key/model/vault setup
  pet memory {add|list|rm|clear}
  pet vault {set|index|clear|status}
  pet rss {list|add|rm|fetch}
  pet history {show|clear}
"""

from __future__ import annotations

import logging
import sys

import click
from rich.prompt import IntPrompt, Prompt

from pet.chat import ChatService
from pet.config import (
    DEFAULT_MODELS, VENDORS, get_api_key, get_model, get_vault_path,
    get_vendor, is_configured, set_api_key, set_model, set_vault_path,
    set_vendor,
)
from pet.knowledge import KnowledgeBase
from pet.render import (
    confirm_tool_call, console, print_error, print_info,
    print_memory_saved, stream_assistant_response,
)
from pet.rss import get_feed_manager
from pet.tools import ToolDispatcher

log = logging.getLogger(__name__)

# Subcommand names — used to disambiguate `pet "free text"` from `pet <subcmd>`.
KNOWN_SUBCOMMANDS = {"config", "memory", "vault", "rss", "history", "skills"}


# ── Shared factory ────────────────────────────────────────────────────────

def _make_chat(kb: KnowledgeBase) -> ChatService:
    """Build a ChatService with confirm + auto-reindex wired in."""
    def _on_vault_write() -> None:
        vault = get_vault_path()
        if not vault:
            return
        try:
            kb.index_vault(vault)
        except Exception as exc:
            log.warning("auto-reindex failed: %s", exc)

    dispatcher = ToolDispatcher(
        confirm=confirm_tool_call,
        on_vault_write=_on_vault_write,
    )
    chat = ChatService(knowledge_base=kb, dispatcher=dispatcher)

    # Memories are injected into the system prompt on every startup.
    memories = kb.get_memories()
    if memories:
        chat.update_system_prompt(memories)

    return chat


def _ensure_configured() -> bool:
    """Return True if API key is set, else launch wizard. Returns False if user bailed."""
    if is_configured():
        return True
    print_info("first-run setup — let's pick a vendor and key.")
    run_config_wizard()
    return is_configured()


# ── Setup wizard (shared between `pet config` and `/config`) ─────────────

def run_config_wizard() -> None:
    """Interactive setup: vendor, API key, model, vault path."""
    console.rule("[bold cyan]DesktopPet setup[/bold cyan]")

    # Vendor
    current_vendor = get_vendor()
    console.print("Pick a vendor:")
    for i, v in enumerate(VENDORS, 1):
        marker = " [dim](current)[/dim]" if v == current_vendor else ""
        console.print(f"  {i}. {v}{marker}")
    default_idx = VENDORS.index(current_vendor) + 1 if current_vendor in VENDORS else 1
    idx = IntPrompt.ask("vendor", default=default_idx,
                        choices=[str(i) for i in range(1, len(VENDORS) + 1)])
    vendor = VENDORS[idx - 1]
    set_vendor(vendor)

    # API key
    existing = get_api_key(vendor)
    hint = f" [dim](leave blank to keep existing)[/dim]" if existing else ""
    api_key = Prompt.ask(f"{vendor} API key{hint}", password=True, default="")
    if api_key:
        set_api_key(vendor, api_key)
    elif not existing:
        print_error("an API key is required to chat.")
        return

    # Model
    models = DEFAULT_MODELS.get(vendor, [])
    current_model = get_model(vendor)
    console.print(f"Pick a model for {vendor}:")
    for i, m in enumerate(models, 1):
        marker = " [dim](current)[/dim]" if m == current_model else ""
        console.print(f"  {i}. {m}{marker}")
    console.print(f"  0. [dim]custom...[/dim]")
    default_idx = (models.index(current_model) + 1) if current_model in models else 1
    idx = IntPrompt.ask("model", default=default_idx,
                        choices=[str(i) for i in range(0, len(models) + 1)])
    if idx == 0:
        model = Prompt.ask("custom model name (litellm format)")
    else:
        model = models[idx - 1]
    set_model(vendor, model)

    # Vault path
    current_vault = get_vault_path()
    vault = Prompt.ask("Obsidian vault path [dim](optional, blank to skip)[/dim]",
                       default=current_vault)
    if vault.strip():
        set_vault_path(vault.strip())

    print_info(f"saved: vendor={vendor}, model={get_model(vendor)}, "
               f"vault={get_vault_path() or '(unset)'}")


# ── Click group ───────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--model", "model_override", default=None,
              help="Override the configured model for this invocation.")
@click.pass_context
def cli(ctx: click.Context, model_override: str | None) -> None:
    """DesktopPet CLI — terminal companion for LLM chat."""
    if ctx.invoked_subcommand is not None:
        return
    # No subcommand → REPL.
    if not _ensure_configured():
        return
    _run_repl(model_override=model_override)


# ── pet config ────────────────────────────────────────────────────────────

@cli.command()
def config() -> None:
    """Interactive setup: pick vendor, enter API key, choose model, set vault path."""
    run_config_wizard()


# ── pet memory ────────────────────────────────────────────────────────────

@cli.group()
def memory() -> None:
    """Manage persistent memories injected into the system prompt."""


@memory.command("add")
@click.argument("text")
def memory_add(text: str) -> None:
    """Add a memory."""
    kb = KnowledgeBase()
    kb.add_memory(text)
    print_memory_saved(text)


@memory.command("list")
def memory_list() -> None:
    """List stored memories."""
    kb = KnowledgeBase()
    mems = kb.get_memories()
    if not mems:
        print_info("no memories stored.")
        return
    for i, m in enumerate(mems):
        console.print(f"[dim]{i}[/dim]  {m}")


@memory.command("rm")
@click.argument("index", type=int)
def memory_rm(index: int) -> None:
    """Remove memory at INDEX (0-based, as shown by `pet memory list`)."""
    kb = KnowledgeBase()
    if kb.remove_memory(index):
        print_info(f"removed memory at index {index}.")
    else:
        print_error("no memory at that index.")


@memory.command("clear")
def memory_clear() -> None:
    """Delete all memories."""
    kb = KnowledgeBase()
    kb.set_memories([])
    print_info("all memories cleared.")


# ── pet vault ─────────────────────────────────────────────────────────────

@cli.group()
def vault() -> None:
    """Manage the Obsidian vault used for RAG."""


@vault.command("set")
@click.argument("path", type=click.Path(exists=True, file_okay=False))
def vault_set(path: str) -> None:
    """Set the Obsidian vault path."""
    set_vault_path(path)
    print_info(f"vault path set to {path}")


@vault.command("index")
def vault_index() -> None:
    """Index (or re-index) the configured vault."""
    vault_path = get_vault_path()
    if not vault_path:
        print_error("no vault path configured. run `pet vault set <path>` first.")
        return
    kb = KnowledgeBase()
    _index_with_progress(kb, vault_path)


@vault.command("clear")
def vault_clear() -> None:
    """Drop the entire vector index."""
    KnowledgeBase().clear_index()
    print_info("vector index cleared.")


@vault.command("status")
def vault_status() -> None:
    """Show vault path and indexed-chunk count."""
    vault_path = get_vault_path() or "(unset)"
    kb = KnowledgeBase()
    console.print(f"vault: [cyan]{vault_path}[/cyan]")
    console.print(f"indexed chunks: [cyan]{kb.collection_count()}[/cyan]")


# ── pet rss ───────────────────────────────────────────────────────────────

@cli.group()
def rss() -> None:
    """Manage RSS feeds the LLM can fetch via tool calls."""


@rss.command("list")
def rss_list() -> None:
    """Show configured feeds."""
    mgr = get_feed_manager()
    feeds = mgr.list_feeds()
    if not feeds:
        print_info("no feeds configured.")
        return
    for url in feeds:
        console.print(f"  {url}")


@rss.command("add")
@click.argument("url")
def rss_add(url: str) -> None:
    """Add a feed URL."""
    if get_feed_manager().add_feed(url):
        print_info(f"added: {url}")
    else:
        print_info(f"already present: {url}")


@rss.command("rm")
@click.argument("url")
def rss_rm(url: str) -> None:
    """Remove a feed URL."""
    if get_feed_manager().remove_feed(url):
        print_info(f"removed: {url}")
    else:
        print_error(f"not found: {url}")


@rss.command("fetch")
@click.argument("url", required=False)
@click.option("--max", "max_items", default=10, show_default=True,
              help="Number of items per feed.")
def rss_fetch(url: str | None, max_items: int) -> None:
    """Fetch a feed (or all configured feeds if URL omitted)."""
    mgr = get_feed_manager()
    if url:
        items = mgr.fetch_feed(url, max_items=max_items)
        _print_rss_items(url, items)
    else:
        for u, items in mgr.fetch_all_feeds(max_items_per_feed=max_items).items():
            _print_rss_items(u, items)


# ── pet history ───────────────────────────────────────────────────────────

@cli.group()
def history() -> None:
    """Manage chat history persistence."""


@history.command("show")
def history_show() -> None:
    """Print the saved conversation."""
    from pet.chat import SYSTEM_PROMPT
    from pet.history import load_history
    msgs = load_history(SYSTEM_PROMPT)
    for msg in msgs:
        role = msg.get("role", "?")
        if role == "system":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
        console.rule(f"[dim]{role}[/dim]")
        console.print(content or "")
    console.rule()


@history.command("clear")
def history_clear() -> None:
    """Delete the saved conversation."""
    from pet.history import clear_history as wipe
    wipe()
    print_info("history cleared.")


# ── pet skills ────────────────────────────────────────────────────────────

@cli.group()
def skills() -> None:
    """Browse and manage cybersecurity skills."""


@skills.command("sync")
def skills_sync() -> None:
    """Download and cache skills from the Anthropic-Cybersecurity-Skills repository."""
    from pet.skills import sync_skills
    count = sync_skills()
    if count > 0:
        print_info(f"synced {count} skills")
    else:
        print_error("failed to sync skills")


@skills.command("list")
@click.option("--domain", default=None, help="Filter by domain (e.g., 'Cloud Security')")
def skills_list(domain: str | None) -> None:
    """List available skills, optionally filtered by domain."""
    from pet.skills import list_skills, get_domains, get_skill

    all_skills = list_skills(domain=domain)
    if not all_skills:
        if domain:
            print_info(f"no skills found in domain '{domain}'")
            console.print("Available domains:")
            for d in get_domains():
                console.print(f"  {d}")
        else:
            print_info("no skills indexed. Run `pet skills sync` first.")
        return

    console.rule(f"[cyan]{len(all_skills)} skills[/cyan]" + (f" in {domain}" if domain else ""))
    for skill in all_skills:
        skill_id = skill.get("id", "")
        name = skill.get("name", skill_id)
        desc = skill.get("description", "")
        domain_str = skill.get("domain", "")
        domain_label = f" [dim]({domain_str})[/dim]" if domain_str else ""
        console.print(f"[cyan]{skill_id}[/cyan]{domain_label}")
        console.print(f"  {desc}")


@skills.command("search")
@click.argument("query")
def skills_search(query: str) -> None:
    """Search for skills by name, description, tags, or domain."""
    from pet.skills import search_skills

    results = search_skills(query)
    if not results:
        print_info(f"no skills match '{query}'")
        return

    console.rule(f"[cyan]{len(results)} match[/cyan]")
    for skill in results:
        skill_id = skill.get("id", "")
        name = skill.get("name", skill_id)
        desc = skill.get("description", "")
        domain = skill.get("domain", "")
        domain_label = f" [dim]({domain})[/dim]" if domain else ""
        console.print(f"[cyan]{skill_id}[/cyan]{domain_label}")
        console.print(f"  {desc}")


@skills.command("show")
@click.argument("skill_id")
def skills_show(skill_id: str) -> None:
    """Display full details of a skill."""
    from pet.skills import get_skill

    skill = get_skill(skill_id)
    if not skill:
        print_error(f"skill '{skill_id}' not found")
        return

    meta = skill.get("metadata", {})
    content = skill.get("content", "")

    # Header
    console.rule(f"[bold cyan]{meta.get('name', skill_id)}[/bold cyan]")
    console.print(f"[dim]ID: {skill_id}[/dim]")

    # Metadata
    if meta.get("description"):
        console.print(f"\n[bold]Description[/bold]")
        console.print(meta["description"])
    if meta.get("domain"):
        console.print(f"\n[bold]Domain:[/bold] {meta['domain']}", end="")
        if meta.get("subdomain"):
            console.print(f" › {meta['subdomain']}")
        else:
            console.print()
    if meta.get("tags"):
        console.print(f"[bold]Tags:[/bold] {', '.join(meta['tags'])}")
    if meta.get("author"):
        console.print(f"[bold]Author:[/bold] {meta['author']}")
    if meta.get("version"):
        console.print(f"[bold]Version:[/bold] {meta['version']}")

    # Content
    if content:
        console.rule("[cyan]Workflow[/cyan]")
        console.print(content)


# ── Internal runners ──────────────────────────────────────────────────────

def _run_repl(model_override: str | None = None) -> None:
    from pet.repl import REPL  # late import: prompt_toolkit is heavyweight

    kb = KnowledgeBase()
    chat = _make_chat(kb)
    if model_override:
        chat.model = model_override
    REPL(chat, kb).run()


def _run_one_shot(question: str, model_override: str | None = None) -> None:
    if not _ensure_configured():
        sys.exit(1)
    kb = KnowledgeBase()
    chat = _make_chat(kb)
    if model_override:
        chat.model = model_override
    events = chat.send_message(question)
    stream_assistant_response(events)


def _index_with_progress(kb: KnowledgeBase, vault_path: str) -> None:
    from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

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

        indexed = kb.index_vault(vault_path, on_progress=on_progress)

    print_info(f"indexed {indexed} files.")


def _print_rss_items(url: str, items: list[dict]) -> None:
    console.rule(f"[cyan]{url}[/cyan]")
    if not items:
        print_info("(no items)")
        return
    for item in items:
        console.print(f"[bold]{item.get('title', '(no title)')}[/bold]")
        if item.get("published"):
            console.print(f"  [dim]{item['published']}[/dim]")
        if item.get("link"):
            console.print(f"  [blue]{item['link']}[/blue]")


# ── Entry point ───────────────────────────────────────────────────────────

def main() -> None:
    """Console-script entry point. Dispatches `pet "free text"` to one-shot mode."""
    # If the first non-flag argument doesn't match a known subcommand, treat the
    # whole thing as a one-shot prompt. This makes `pet "what's CVE..."` Just Work
    # while keeping `pet config`, `pet memory list`, etc. routed through Click.
    args = sys.argv[1:]
    looks_like_question = (
        bool(args)
        and not args[0].startswith("-")
        and args[0] not in KNOWN_SUBCOMMANDS
    )
    if looks_like_question:
        _run_one_shot(" ".join(args))
        return
    cli()


if __name__ == "__main__":
    main()
