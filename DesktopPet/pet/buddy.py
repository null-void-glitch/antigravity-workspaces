"""
buddy.py — small ASCII mascot rendered in the REPL header.

Three states swap in during the chat lifecycle: idle while waiting for input,
typing while the model is streaming a response, and heart on a "thank you".
"""

from __future__ import annotations

from enum import Enum


class BuddyState(str, Enum):
    IDLE = "idle"
    TYPING = "typing"
    HEART = "heart"


# Three small frames. Width matches across states so the header doesn't reflow.
BUDDIES: dict[BuddyState, str] = {
    BuddyState.IDLE:   "  /\\_/\\  \n ( o.o ) \n  > ^ <  ",
    BuddyState.TYPING: "  /\\_/\\  \n ( -.- ) \n  > ~ <  ",
    BuddyState.HEART:  "  /\\_/\\  \n ( ^.^ ) \n  > ♥ <  ",
}

# Single-character emoji faces used in the inline rule and the bottom toolbar.
# Same width across all states so reflows don't shift other text around.
INLINE_FACES: dict[BuddyState, str] = {
    BuddyState.IDLE:   "(•‿•)",
    BuddyState.TYPING: "(◐‿◐)",
    BuddyState.HEART:  "(♥‿♥)",
}


def render_buddy(state: BuddyState) -> str:
    """Return the multi-line ASCII frame for *state*."""
    return BUDDIES.get(state, BUDDIES[BuddyState.IDLE])


# Trigger phrases that should swap the buddy into HEART briefly.
THANK_YOU_PHRASES = [
    "thanks", "nice", "perfect", "good job",
    "thank you", "that works", "solved", "done it",
]


def is_thank_you(text: str) -> bool:
    """Return True if *text* contains any thank-you phrase (case-insensitive)."""
    lowered = text.lower()
    return any(phrase in lowered for phrase in THANK_YOU_PHRASES)
