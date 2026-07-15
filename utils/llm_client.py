"""LLM client selection.

Ollama exposes an OpenAI-compatible endpoint (`/v1/chat/completions`), so a
local model needs no separate SDK -- just point the official `openai` client
at Ollama's base_url instead of api.openai.com. Set LLM_PROVIDER=ollama in
.env to use a local model (default: qwen3:8b) with zero API cost; leave it
unset/"openai" to use a real OpenAI key.
"""
import json
import re
import os

from openai import OpenAI

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")


def has_llm_configured() -> bool:
    return provider() == "ollama" or bool(os.getenv("OPENAI_API_KEY"))


def provider() -> str:
    return os.getenv("LLM_PROVIDER", "openai").lower()


def get_client() -> OpenAI:
    if provider() == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return OpenAI(base_url=base_url, api_key="ollama")  # api_key is unused but required by the SDK
    return OpenAI()


def get_model() -> str:
    if provider() == "ollama":
        return os.getenv("OLLAMA_MODEL", "qwen3:8b")
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def parse_json_response(content: str) -> dict:
    """Strip reasoning-model artifacts (<think> blocks, ```json fences) before parsing.

    Some local reasoning models (qwen3 included, depending on version/quantization)
    can leak <think>...</think> or markdown fences into message content even when
    response_format=json_object is requested. The OpenAI API never does this, so
    this is a no-op there.
    """
    cleaned = _THINK_TAG_RE.sub("", content).strip()
    cleaned = _CODE_FENCE_RE.sub("", cleaned).strip()
    return json.loads(cleaned)
