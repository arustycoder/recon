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
    "api_stream_url",
    "api_cancel_url_template",
    "api_providers_url",
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


def _env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def provider_settings_from_env() -> ProviderSettings:
    timeout_raw = (
        _env("RECON_REQUEST_TIMEOUT_SECONDS", "DARKFACTORY_REQUEST_TIMEOUT_SECONDS")
        or os.getenv("OPENAI_TIMEOUT_SECONDS")
        or "60"
    )
    try:
        timeout_value = max(5, min(int(timeout_raw), 300))
    except ValueError:
        timeout_value = 60

    return ProviderSettings(
        provider=_env("RECON_LLM_PROVIDER", "DARKFACTORY_LLM_PROVIDER"),
        ollama_url=_env("RECON_OLLAMA_URL", "DARKFACTORY_OLLAMA_URL")
        or "http://127.0.0.1:11434/v1",
        ollama_model=_env("RECON_OLLAMA_MODEL", "DARKFACTORY_OLLAMA_MODEL"),
        ollama_api_key=(
            _env("RECON_OLLAMA_API_KEY", "DARKFACTORY_OLLAMA_API_KEY") or "ollama"
        ),
        openai_base_url=(
            _env("RECON_OPENAI_BASE_URL", "DARKFACTORY_OPENAI_BASE_URL")
            or os.getenv("OPENAI_BASE_URL", "").strip()
        ),
        openai_api_key=(
            _env("RECON_OPENAI_API_KEY", "DARKFACTORY_OPENAI_API_KEY")
            or os.getenv("OPENAI_API_KEY", "").strip()
        ),
        openai_model=(
            _env("RECON_OPENAI_MODEL", "DARKFACTORY_OPENAI_MODEL")
            or os.getenv("OPENAI_MODEL", "").strip()
        ),
        api_url=_env("RECON_API_URL", "DARKFACTORY_API_URL"),
        api_health_url=_env("RECON_API_HEALTH_URL", "DARKFACTORY_API_HEALTH_URL"),
        api_stream_url=_env("RECON_API_STREAM_URL", "DARKFACTORY_API_STREAM_URL"),
        api_cancel_url_template=_env(
            "RECON_API_CANCEL_URL_TEMPLATE",
            "DARKFACTORY_API_CANCEL_URL_TEMPLATE",
        ),
        api_providers_url=_env("RECON_API_PROVIDERS_URL", "DARKFACTORY_API_PROVIDERS_URL"),
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


def derive_http_stream_url(api_url: str, explicit_stream_url: str = "") -> str:
    explicit = explicit_stream_url.strip()
    if explicit:
        return explicit

    base = api_url.strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/chat"):
        return base + "/stream"
    if base.endswith("/api/chat"):
        return base + "/stream"
    return base + "/stream"


def derive_http_cancel_url(
    api_url: str,
    request_id: str,
    explicit_cancel_url_template: str = "",
) -> str:
    request = request_id.strip()
    if not request:
        return ""

    template = explicit_cancel_url_template.strip()
    if template:
        if "{request_id}" in template:
            return template.replace("{request_id}", request)
        return template.rstrip("/") + "/" + request

    base = api_url.strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/chat"):
        return f"{base}/{request}/cancel"
    if base.endswith("/api/chat"):
        return f"{base}/{request}/cancel"
    return f"{base}/{request}/cancel"


def derive_http_providers_url(api_url: str, explicit_providers_url: str = "") -> str:
    explicit = explicit_providers_url.strip()
    if explicit:
        return explicit

    base = api_url.strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/chat"):
        return base[: -len("/chat")] + "/providers"
    if base.endswith("/api/chat"):
        return base[: -len("/api/chat")] + "/api/providers"
    return base + "/providers"
