"""
Gemini provider — uses new google.genai SDK.
Falls back to old google.generativeai if new one not installed.
"""
import os
from .base import BaseLLM

# Try new SDK first
try:
    from google import genai
    from google.genai import types
    _SDK = "new"
except ImportError:
    try:
        import google.generativeai as genai_old
        _SDK = "old"
    except ImportError:
        _SDK = None


class GeminiLLM(BaseLLM):
    def __init__(self, model="gemini-2.0-flash", api_key=None):
        self.model_name = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._client = None

    def is_available(self) -> bool:
        return _SDK is not None and bool(self.api_key)

    def _init_new(self):
        if not self._client:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _init_old(self):
        if not self._client:
            genai_old.configure(api_key=self.api_key)
            self._client = genai_old.GenerativeModel(self.model_name)
        return self._client

    def send(self, messages: list, stream: bool = True):
        if not self.api_key:
            raise RuntimeError("No GEMINI_API_KEY set.")

        if _SDK == "new":
            yield from self._send_new(messages, stream)
        elif _SDK == "old":
            yield from self._send_old(messages, stream)
        else:
            raise RuntimeError(
                "Gemini SDK not installed.\n"
                "Run: pip install google-genai"
            )

    def _send_new(self, messages: list, stream: bool):
        client = self._init_new()

        # Build contents list
        system_parts = []
        contents = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_parts.append(content)
            elif role == "user":
                contents.append(types.Content(role="user",
                    parts=[types.Part(text=content)]))
            elif role == "assistant":
                contents.append(types.Content(role="model",
                    parts=[types.Part(text=content)]))

        system_instruction = "\n\n".join(system_parts) if system_parts else None

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=8192,
        )

        if stream:
            for chunk in client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config,
            ):
                if chunk.text:
                    yield chunk.text
        else:
            resp = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            yield resp.text

    def _send_old(self, messages: list, stream: bool):
        """Fallback to old SDK (shows FutureWarning but works)."""
        import warnings
        warnings.filterwarnings("ignore", category=FutureWarning)

        model = self._init_old()
        system = ""
        history = []

        for msg in messages:
            r, content = msg["role"], msg["content"]
            if r == "system":
                system += content + "\n"
            elif r == "user":
                history.append({"role": "user", "parts": [content]})
            elif r == "assistant":
                history.append({"role": "model", "parts": [content]})

        if system and history and history[0]["role"] == "user":
            history[0]["parts"][0] = system + "\n\n" + history[0]["parts"][0]

        if not history:
            return

        last = history[-1]["parts"][0]
        chat = model.start_chat(history=history[:-1])

        if stream:
            for chunk in chat.send_message(last, stream=True):
                if chunk.text:
                    yield chunk.text
        else:
            yield chat.send_message(last).text

    def list_models(self):
        return [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite-preview-02-05",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
