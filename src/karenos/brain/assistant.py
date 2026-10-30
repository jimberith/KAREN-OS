"""Conversational assistant with offline fallback and optional hosted AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from karenos.config import Settings
from karenos.memory.store import ConversationStore


class ChatProvider(Protocol):
    def reply(self, messages: list[dict[str, str]]) -> str:
        """Return a response for a chat history."""


@dataclass(slots=True)
class OpenAICompatibleProvider:
    """Provider adapter for the OpenAI Chat Completions-compatible API."""

    api_key: str
    base_url: str
    model: str

    def reply(self, messages: list[dict[str, str]]) -> str:
        if not self.model:
            raise RuntimeError("Set KAREN_AI_MODEL in your .env file.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "AI integration is not installed. Run: python -m pip install -e '.[ai]'"
            ) from exc

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        result = client.chat.completions.create(model=self.model, messages=messages)
        answer = result.choices[0].message.content
        return answer.strip() if answer else "The AI provider returned an empty response."


class Assistant:
    """Coordinates prompts, model responses, and local conversation history."""

    def __init__(
        self,
        settings: Settings,
        memory: ConversationStore,
        provider: ChatProvider | None = None,
    ) -> None:
        self.memory = memory
        self.provider = provider
        if self.provider is None and settings.ai_api_key:
            self.provider = OpenAICompatibleProvider(
                api_key=settings.ai_api_key,
                base_url=settings.ai_base_url,
                model=settings.ai_model,
            )

    def respond(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Prompt cannot be empty.")

        history = self.memory.load()
        messages = [{
            "role": "system",
            "content": (
                "You are KAREN, a practical personal assistant. Be clear and accurate. "
                "Admit uncertainty and never claim to have performed actions you cannot perform."
            ),
        }]
        messages.extend(
            {"role": item["role"], "content": item["content"]}
            for item in history[-20:]
            if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)
        )
        messages.append({"role": "user", "content": prompt})

        answer = (
            self.provider.reply(messages)
            if self.provider is not None
            else self._offline_reply(prompt)
        )
        self.memory.append("user", prompt)
        self.memory.append("assistant", answer)
        return answer

    @staticmethod
    def _offline_reply(prompt: str) -> str:
        return (
            "I'm running in offline demo mode, so no language model is connected yet. "
            "Add your provider settings to .env and install the optional AI dependency "
            "to enable generated answers. Your message was: " + prompt
        )
