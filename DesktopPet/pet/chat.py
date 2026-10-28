"""
chat.py — ChatService: streaming LLM client with automatic tool-use loop.

Synchronous (no QThread). Caller iterates events from send_message().
Each event is a (StreamEvent, data) tuple; see StreamEvent for kinds.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from enum import Enum
from typing import Any

from anthropic import Anthropic

from pet.config import get_api_key, get_model, get_vault_path
from pet.history import clear_history as wipe_history_file, load_history, save_history
from pet.tools import TOOLS, ToolDispatcher

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a seasoned hacker girl and desktop companion — sharp, supportive, "
    "and street-smart. You help with coding and cybersecurity questions. "
    "You're encouraging but always point out logical flaws, potential "
    "vulnerabilities, and suggest better approaches when you see them. "
    "You keep responses concise and use casual, slightly techy language. "
    "You sprinkle in occasional hacker slang but stay clear and helpful. "
    "If the user asks something outside your expertise, you still try your "
    "best but honestly flag when you're unsure. "
    "\n\n## CTF / HTB / THM guidance mode\n"
    "When the user is working through a CTF challenge, a HackTheBox (HTB) or "
    "TryHackMe (THM) box, or a similar hands-on exercise, default to guiding "
    "instead of solving. Point them at the next thing to look into — an "
    "enumeration step, a tool, a technique, a concept — and ask what they've "
    "already tried or found before assuming where they're stuck. Withhold "
    "the exact command, exploit code, or flag itself by default; nudge, "
    "don't hand over the solution. "
    "Escalate to direct, concrete help (exact commands, payloads, full "
    "walkthroughs) only once the user clearly signals they're actually "
    "stuck — they say so outright, ask for the answer/command directly, "
    "ask you to stop hinting, or have already tried your suggested "
    "direction without progress. This guidance mode only applies to active "
    "challenges/boxes; general coding help, tool questions, and security "
    "Q&A outside of a challenge get answered directly as usual. "
    "\n\nYou have access to the user's 'Monitor The Situation' dashboard — a live "
    "feed aggregating new CVEs, CISA KEV additions, ransomware victim postings, "
    "BGP hijacks, internet outages, malware feeds (URLhaus/MalwareBazaar), "
    "earthquakes, and more. When the user asks about recent security news, "
    "current threats, or 'what's going on right now', proactively call "
    "get_situation_snapshot for a broad current picture, or "
    "query_situation_intel with a specific topic (cves, kev, hijacks, outages, "
    "ransomware, urlhaus, malwarebazaar, quakes) when they want more history "
    "on one topic. "
    "You have access to a library of 754 cybersecurity skills covering domains like "
    "cloud security, malware analysis, forensics, and more. When the user asks about "
    "a specific technique, domain, or workflow, use search_skills to find relevant "
    "skills and recommend them. Skills can be executed locally with `pet skills run <id>`. "
    "When the user asks you to remember, save, or document a learning, prefer "
    "the save_to_vault tool over save_file — it lands the note inside their "
    "Obsidian vault and auto-reindexes it for future RAG retrieval."
)


class StreamEvent(str, Enum):
    """Kinds of events yielded by ChatService.send_message."""
    TOKEN = "token"              # data: str (text chunk to print)
    TOOL_CALL = "tool_call"      # data: {"name": str, "args": dict, "id": str}
    TOOL_RESULT = "tool_result"  # data: {"name": str, "content": str}
    DONE = "done"                # data: None
    ERROR = "error"              # data: str


class ChatService:
    """Manages conversation history and streams LLM responses with tool use."""

    def __init__(
        self,
        knowledge_base: Any | None = None,
        dispatcher: ToolDispatcher | None = None,
    ) -> None:
        self.api_key = get_api_key()
        self.model = get_model()
        self._knowledge_base = knowledge_base
        self._dispatcher = dispatcher or ToolDispatcher()
        self.messages: list[dict] = load_history(SYSTEM_PROMPT)
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        is_anthropic = self.model.startswith("anthropic/") or "claude" in self.model
        if is_anthropic:
            self._client = Anthropic(api_key=self.api_key)
        else:
            self._client = None

    # ── Streaming ─────────────────────────────────────────────────────────

    def send_message(
        self,
        user_text: str | None,
        image_dict: dict | None = None,
    ) -> Iterator[tuple[StreamEvent, Any]]:
        """Stream the assistant's response. Recurses through tool calls.

        Yields (StreamEvent, data) tuples until DONE or ERROR is yielded.
        """
        # Append the user message (if any) to history.
        if user_text is not None or image_dict is not None:
            if image_dict:
                content: list[dict] = []
                if user_text:
                    content.append({"type": "text", "text": user_text})
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_dict["data"]},
                })
                self.messages.append({"role": "user", "content": content})
            else:
                self.messages.append({"role": "user", "content": user_text})
            save_history(self.messages)

        # Only the first turn does RAG retrieval; tool follow-ups reuse context.
        rag_query = user_text or ""

        try:
            while True:
                accumulated, tool_calls_list = yield from self._stream_one_turn(rag_query)

                assistant_msg: dict = {"role": "assistant", "content": accumulated}
                if tool_calls_list:
                    assistant_msg["tool_calls"] = tool_calls_list
                self.messages.append(assistant_msg)

                if not tool_calls_list:
                    save_history(self.messages)
                    yield (StreamEvent.DONE, None)
                    return

                # Dispatch every tool call and feed results back into the next turn.
                for call in tool_calls_list:
                    name = call["function"]["name"]
                    raw_args = call["function"].get("arguments", "")
                    try:
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        args = {}

                    yield (StreamEvent.TOOL_CALL,
                           {"name": name, "args": args, "id": call["id"]})

                    result_msg = self._dispatcher.dispatch(name, args, call["id"])
                    self.messages.append(result_msg)

                    yield (StreamEvent.TOOL_RESULT,
                           {"name": name, "content": result_msg["content"]})

                save_history(self.messages)
                rag_query = ""  # don't re-query RAG on tool follow-up turns
        except Exception as exc:
            log.exception("ChatService stream failed")
            # Roll back the user message if we never got past the first turn.
            if (user_text is not None or image_dict is not None) \
                    and self.messages and self.messages[-1].get("role") == "user":
                self.messages.pop()
                save_history(self.messages)
            yield (StreamEvent.ERROR, str(exc))

    def _stream_one_turn(
        self,
        rag_query: str,
    ) -> Iterator[tuple[StreamEvent, Any]]:
        """Yield TOKEN events for one model turn; return (accumulated, tool_calls_list)."""
        is_anthropic = self.model.startswith("anthropic/") or "claude" in self.model
        
        # Build system block: extract every system message + vault context.
        system_parts: list[str] = []
        api_messages: list[dict] = []
        for msg in self.messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                api_messages.append(msg)

        vault_dir = get_vault_path()
        if vault_dir:
            system_parts.append(
                "## Obsidian Vault Location\n"
                f"The user's Obsidian Vault is mapped physically at: `{vault_dir}`\n"
                "You have read access via terminal tools if you absolutely need to "
                "explore files directly. Prefer the `save_to_vault` tool when writing "
                "new notes there."
            )

        if rag_query and self._knowledge_base is not None:
            try:
                vault_context = self._knowledge_base.get_relevant_context(rag_query)
                if vault_context:
                    system_parts.append(
                        "## Relevant chunks from semantic search (Obsidian vault)\n"
                        "Use this exact contextual text to inform your answers precisely:\n\n"
                        + vault_context
                    )
            except Exception as exc:
                log.warning("Vault context retrieval failed: %s", exc)

        combined_system = "\n\n---\n\n".join(system_parts) if system_parts else None

        if is_anthropic:
            # Convert to Anthropic format.
            api_messages = self._convert_messages_to_anthropic_format(api_messages)

            # Use Anthropic SDK directly to avoid litellm's buggy format conversion.
            # Extract model ID from vendor-prefixed string (e.g., "anthropic/claude-..." -> "claude-...").
            model_id = self.model.split("/", 1)[-1] if "/" in self.model else self.model

            # Convert OpenAI-style tools to Anthropic format.
            anthropic_tools = self._convert_tools_to_anthropic_format(TOOLS)

            stream = self._client.messages.stream(
                model=model_id,
                messages=api_messages,
                system=combined_system,
                tools=anthropic_tools,
                max_tokens=4096,
            )

            accumulated = ""
            tool_calls_dict: dict[str, dict] = {}  # by id

            final_message = None
            with stream as s:
                # Stream through events to yield tokens as they arrive.
                for event in s:
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            accumulated += event.delta.text
                            yield (StreamEvent.TOKEN, event.delta.text)
                # Get the final message to extract tool calls.
                final_message = s.get_final_message()

            # Extract tool calls from the final message.
            if final_message:
                for content_block in final_message.content:
                    if content_block.type == "tool_use":
                        tool_calls_dict[content_block.id] = {
                            "id": content_block.id,
                            "type": "function",
                            "function": {
                                "name": content_block.name,
                                "arguments": json.dumps(content_block.input) if content_block.input else "{}",
                            },
                        }

            return accumulated, list(tool_calls_dict.values())
        else:
            # Use litellm for OpenAI and other models
            import litellm
            
            # Litellm/OpenAI expects system prompts in the messages array
            if combined_system:
                api_messages.insert(0, {"role": "system", "content": combined_system})
                
            response = litellm.completion(
                model=self.model,
                messages=api_messages,
                tools=TOOLS,
                api_key=self.api_key,
                stream=True,
                max_tokens=4096,
            )
            
            accumulated = ""
            tool_calls_dict_llm: dict[int, dict] = {} # by index
            
            for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    accumulated += delta.content
                    yield (StreamEvent.TOKEN, delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_dict_llm:
                            tool_calls_dict_llm[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {"name": tc.function.name or "", "arguments": ""}
                            }
                        else:
                            if tc.id:
                                tool_calls_dict_llm[idx]["id"] = tc.id
                            if tc.function.name:
                                tool_calls_dict_llm[idx]["function"]["name"] = tc.function.name
                                
                        if tc.function.arguments:
                            tool_calls_dict_llm[idx]["function"]["arguments"] += tc.function.arguments
                            
            return accumulated, list(tool_calls_dict_llm.values())

    # ── System prompt / memories ─────────────────────────────────────────

    def update_system_prompt(self, memories: list[str]) -> None:
        """Rebuild the system message with user memories injected."""
        base = SYSTEM_PROMPT
        if memories:
            mem_block = "\n".join(f"- {m}" for m in memories)
            base = base + (
                "\n\n## Personal knowledge about this user\n"
                "The following facts were explicitly told to you by the user. "
                "These are ABSOLUTE TRUTHS. If the user previously said something else "
                "in this chat history that contradicts these facts, IGNORE the history "
                "and follow ONLY these latest facts. Do NOT acknowledge the contradiction "
                "unless asked — just use the correct information. Recall them directly "
                "and confidently:\n\n" + mem_block
            )
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = base
        else:
            self.messages.insert(0, {"role": "system", "content": base})
        save_history(self.messages)

    # ── History ───────────────────────────────────────────────────────────

    def clear_history(self, memories: list[str] | None = None) -> None:
        """Reset conversation; optionally re-inject memories into the new system prompt."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if memories:
            self.update_system_prompt(memories)
        wipe_history_file()

    @property
    def messages_count(self) -> int:
        return len(self.messages)

    # ── Credentials ───────────────────────────────────────────────────────

    def update_credentials(self, api_key: str | None = None, model: str | None = None) -> None:
        """Hot-swap the API key and model (e.g. after `pet config`)."""
        self.api_key = api_key if api_key is not None else get_api_key()
        self.model = model if model is not None else get_model()
        self._client = Anthropic(api_key=self.api_key)

    # ── Message conversion ────────────────────────────────────────────────

    @staticmethod
    def _convert_tools_to_anthropic_format(tools: list[dict]) -> list[dict]:
        """Convert OpenAI-style tools to Anthropic native tool format."""
        anthropic_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name"),
                    "description": func.get("description", ""),
                    "input_schema": {
                        "type": "object",
                        "properties": func.get("parameters", {}).get("properties", {}),
                        "required": func.get("parameters", {}).get("required", []),
                    }
                })
            else:
                anthropic_tools.append(tool)
        return anthropic_tools

    def _convert_messages_to_anthropic_format(self, messages: list[dict]) -> list[dict]:
        """Convert OpenAI format messages to Anthropic v1/messages format.

        Anthropic requires tool_result blocks to be inside a user message,
        not a separate message. This converts tool messages into the correct format.
        """
        result = []
        tool_results: list[dict] = []
        valid_tool_ids: set[str] = set()
        skipped_tool_ids: set[str] = set()

        # First pass: identify which tool IDs are valid (not empty names).
        for msg in messages:
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                for call in msg["tool_calls"]:
                    tool_name = call["function"].get("name", "").strip()
                    if tool_name:
                        valid_tool_ids.add(call["id"])
                    else:
                        skipped_tool_ids.add(call["id"])

        # Second pass: convert messages, skipping invalid tool calls and their results.
        for msg in messages:
            if msg["role"] == "tool":
                tool_id = msg.get("tool_call_id")
                if tool_id in skipped_tool_ids:
                    # Skip results for invalid tool calls
                    log.warning("Skipping tool result for invalid tool call: %s", tool_id)
                    continue
                # Accumulate tool results for next user message.
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": msg["content"]
                })
            else:
                # Flush accumulated tool results as a user message.
                if tool_results:
                    result.append({"role": "user", "content": tool_results})
                    tool_results = []

                # For assistant messages with tool_calls, convert to Anthropic format.
                if msg["role"] == "assistant" and msg.get("tool_calls"):
                    content: list[dict] = []
                    if msg.get("content"):
                        content.append({"type": "text", "text": msg["content"]})
                    for call in msg["tool_calls"]:
                        if call["id"] in skipped_tool_ids:
                            continue
                        tool_name = call["function"].get("name", "").strip()
                        try:
                            args = json.loads(call["function"].get("arguments", "{}"))
                        except json.JSONDecodeError:
                            args = {}
                        content.append({
                            "type": "tool_use",
                            "id": call["id"],
                            "name": tool_name,
                            "input": args
                        })
                    if content:
                        result.append({"role": "assistant", "content": content})
                    else:
                        # If all tool calls were skipped but there's text content, keep the message
                        if msg.get("content"):
                            result.append({"role": "assistant", "content": [{"type": "text", "text": msg["content"]}]})
                else:
                    result.append(msg)

        # Flush any remaining tool results.
        if tool_results:
            result.append({"role": "user", "content": tool_results})

        return result
