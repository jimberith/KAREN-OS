"""Optional text-to-speech output."""

from __future__ import annotations


class SpeechOutput:
    """Lazy wrapper around pyttsx3 so base installs need no audio libraries."""

    def __init__(self, rate: int = 175, volume: float = 1.0) -> None:
        self.rate = rate
        self.volume = max(0.0, min(1.0, volume))
        self._engine = None

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError(
                "Speech output is not installed. Run: python -m pip install -e '.[voice]'"
            ) from exc

        if self._engine is None:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)
        self._engine.say(text)
        self._engine.runAndWait()
