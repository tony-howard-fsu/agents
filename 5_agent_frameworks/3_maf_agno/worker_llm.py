"""Resolves a WORKER_MODEL "provider/model-id" string into what each framework's
OpenAI-compatible client needs: a bare model id, a base_url, and an api_key. One
table so adding a provider is a one-line change picked up by every worker, instead
of each framework hardcoding DeepSeek's endpoint and key.
"""

from __future__ import annotations

import os

PROVIDERS = {
    "deepseek": {"base_url": "https://api.deepseek.com", "api_key_env": "DEEPSEEK_API_KEY"},
    "openai": {"base_url": None, "api_key_env": "OPENAI_API_KEY"},  # None: let the client use OpenAI's own default
    "groq": {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    "ollama": {"base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"), "api_key_env": None},
}


def resolve(model_spec: str) -> tuple[str, str | None, str]:
    """Split "provider/model-id" into (model_id, base_url, api_key).

    base_url is None when the client's own default is correct (OpenAI). api_key is a
    harmless placeholder for a provider that needs none (a local Ollama server), since
    every one of these clients requires some non-empty string.
    """
    provider, _, model_id = model_spec.partition("/")
    if not model_id:
        raise ValueError(f"WORKER_MODEL '{model_spec}' is missing a provider prefix, e.g. 'deepseek/{model_spec}'.")
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}' in WORKER_MODEL '{model_spec}'. Known: {', '.join(PROVIDERS)}.")
    entry = PROVIDERS[provider]
    api_key = os.environ[entry["api_key_env"]] if entry["api_key_env"] else "not-needed"
    return model_id, entry["base_url"], api_key
