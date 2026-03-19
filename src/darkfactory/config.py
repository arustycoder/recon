from __future__ import annotations

import os
from pathlib import Path

from .models import ProviderSettings


DEFAULT_PROVIDER_KEYS = (
    "provider",
    "ollama_url",
    "ollama_model",
    "ollama_api_key",
    "openai_base_url",
    "openai_api_key",
    "openai_model",
    "api_url",
    "api_health_url",
    "request_timeout_seconds",
)


def load_env() -> None:
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def provider_settings_from_env() -> ProviderSettings:
    timeout_raw = (
        os.getenv("DARKFACTORY_REQUEST_TIMEOUT_SECONDS")
        or os.getenv("OPENAI_TIMEOUT_SECONDS")
        or "60"
    )
    try:
        timeout_value = max(5, min(int(timeout_raw), 300))
    except ValueError:
        timeout_value = 60

    return ProviderSettings(
        provider=os.getenv("DARKFACTORY_LLM_PROVIDER", "").strip(),
        ollama_url=(
            os.getenv("DARKFACTORY_OLLAMA_URL", "").strip() or "http://127.0.0.1:11434/v1"
        ),
        ollama_model=os.getenv("DARKFACTORY_OLLAMA_MODEL", "").strip(),
        ollama_api_key=os.getenv("DARKFACTORY_OLLAMA_API_KEY", "").strip() or "ollama",
        openai_base_url=(
            os.getenv("DARKFACTORY_OPENAI_BASE_URL", "").strip()
            or os.getenv("OPENAI_BASE_URL", "").strip()
        ),
        openai_api_key=(
            os.getenv("DARKFACTORY_OPENAI_API_KEY", "").strip()
            or os.getenv("OPENAI_API_KEY", "").strip()
        ),
        openai_model=(
            os.getenv("DARKFACTORY_OPENAI_MODEL", "").strip()
            or os.getenv("OPENAI_MODEL", "").strip()
        ),
        api_url=os.getenv("DARKFACTORY_API_URL", "").strip(),
        api_health_url=os.getenv("DARKFACTORY_API_HEALTH_URL", "").strip(),
        request_timeout_seconds=timeout_value,
    )


def derive_http_health_url(api_url: str, explicit_health_url: str = "") -> str:
    explicit = explicit_health_url.strip()
    if explicit:
        return explicit

    base = api_url.strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/chat"):
        return base[: -len("/chat")] + "/health"
    if base.endswith("/api/chat"):
        return base[: -len("/api/chat")] + "/api/health"
    return base + "/health"
