"""Small, predictable intent router for KAREN OS."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Intent:
    kind: str
    action: dict[str, Any] | None = None


def classify_intent(text: str) -> Intent:
    """Route obvious commands without an extra model call.

    Anything ambiguous stays in ordinary chat. The router never accepts shell
    commands or arbitrary executable names.
    """
    value = re.sub(r"\s+", " ", text.strip().lower())
    if not value:
        return Intent("chat")

    if re.search(r"\b(remember this|remember that|save this note|save a note)\b", value):
        return Intent("remember")
    if re.search(r"\b(what do you remember|search my memory|recall my notes|show my notes)\b", value):
        return Intent("recall")
    if re.search(r"\b(generate|create|draw|make)\b.{0,50}\b(image|picture|illustration|artwork)\b", value):
        return Intent("image_generation")
    if re.search(r"\b(search the web|search online|look this up|latest news|current news|today's news|current weather|weather today|current price|stock price|exchange rate)\b", value):
        return Intent("web_search")

    website_patterns = {
        "youtube": r"\b(open|launch|go to)\s+(youtube|youtube\.com)\b",
        "google": r"\b(open|launch|go to)\s+(google|google\.com)\b",
        "github": r"\b(open|launch|go to)\s+(github|github\.com)\b",
    }
    for target, pattern in website_patterns.items():
        if re.search(pattern, value):
            return Intent("automation", {"name": "open_website", "target": target})

    app_patterns = {
        "calculator": r"\b(open|launch|start)\s+(the\s+)?calculator\b",
        "files": r"\b(open|launch)\s+(file manager|files|downloads)\b",
        "terminal": r"\b(open|launch)\s+(the\s+)?terminal\b",
        "code": r"\b(open|launch)\s+(vs code|visual studio code|vscode)\b",
        "browser": r"\b(open|launch)\s+(my\s+)?browser\b",
    }
    for target, pattern in app_patterns.items():
        if re.search(pattern, value):
            return Intent("automation", {"name": "open_app", "target": target})

    if re.search(r"\b(mute|mute volume|silence the audio)\b", value):
        return Intent("automation", {"name": "volume", "target": "mute"})
    if re.search(r"\b(unmute|turn sound on)\b", value):
        return Intent("automation", {"name": "volume", "target": "unmute"})
    if re.search(r"\b(volume up|increase volume|turn volume up)\b", value):
        return Intent("automation", {"name": "volume", "target": "up"})
    if re.search(r"\b(volume down|decrease volume|turn volume down)\b", value):
        return Intent("automation", {"name": "volume", "target": "down"})
    if re.search(r"\b(system status|system information|battery status|cpu usage|memory usage)\b", value):
        return Intent("automation", {"name": "system_status", "target": "status"})

    return Intent("chat")
