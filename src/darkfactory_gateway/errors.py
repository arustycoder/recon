from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GatewayErrorInfo:
    error_type: str
    detail: str
    http_status_code: int
    provider_health_status: str
    cooldown_reason: str = ""
    retryable: bool = False


@dataclass(slots=True)
class GatewayErrorPolicy:
    error_type: str
    retry_same_provider_sync: bool = False
    cooldown_mode: str = "threshold"


class GatewayProviderError(RuntimeError):
    def __init__(self, error: GatewayErrorInfo) -> None:
        super().__init__(error.detail)
        self.error = error


def classify_gateway_error(detail: str) -> GatewayErrorInfo:
    text = (detail or "").strip()
    lowered = text.lower()

    if not text:
        return GatewayErrorInfo(
            error_type="unknown",
            detail="Unknown provider failure.",
            http_status_code=502,
            provider_health_status="degraded",
        )

    if "429" in lowered or "too many requests" in lowered or "rate limit" in lowered:
        return GatewayErrorInfo(
            error_type="rate_limited",
            detail=text,
            http_status_code=429,
            provider_health_status="rate_limited",
            cooldown_reason="rate_limited",
        )

    if "streaming connection closed before the response completed" in lowered:
        return GatewayErrorInfo(
            error_type="stream_interrupted",
            detail=text,
            http_status_code=502,
            provider_health_status="cooldown",
            cooldown_reason="stream_unstable",
            retryable=True,
        )

    if "timed out" in lowered or "timeout" in lowered or "read operation timed out" in lowered:
        return GatewayErrorInfo(
            error_type="upstream_timeout",
            detail=text,
            http_status_code=504,
            provider_health_status="unreachable",
            retryable=True,
        )

    if any(token in lowered for token in ("connection reset", "connection refused", "dns", "network", "connect error", "all connection attempts failed", "name or service not known")):
        return GatewayErrorInfo(
            error_type="upstream_unreachable",
            detail=text,
            http_status_code=503,
            provider_health_status="unreachable",
            retryable=True,
        )

    if "disabled in registry" in lowered:
        return GatewayErrorInfo(
            error_type="provider_disabled",
            detail=text,
            http_status_code=503,
            provider_health_status="disabled",
        )

    if "cooling down" in lowered:
        return GatewayErrorInfo(
            error_type="provider_cooldown",
            detail=text,
            http_status_code=503,
            provider_health_status="cooldown",
        )

    if "requires openai_base_url" in lowered or "requires openai_model" in lowered or "requires api_url" in lowered or "requires ollama_model" in lowered:
        return GatewayErrorInfo(
            error_type="misconfigured",
            detail=text,
            http_status_code=500,
            provider_health_status="misconfigured",
        )

    if "did not contain assistant text" in lowered or "did not contain 'reply'" in lowered:
        return GatewayErrorInfo(
            error_type="empty_response",
            detail=text,
            http_status_code=502,
            provider_health_status="degraded",
        )

    if any(token in lowered for token in ("invalid json", "json decode", "malformed", "invalid response")):
        return GatewayErrorInfo(
            error_type="invalid_response",
            detail=text,
            http_status_code=502,
            provider_health_status="degraded",
        )

    if any(
        token in lowered
        for token in (
            "404 not found",
            "401",
            "403",
            "client error '400",
            "client error '401",
            "client error '403",
            "client error '404",
            "not found",
        )
    ):
        return GatewayErrorInfo(
            error_type="upstream_http_error",
            detail=text,
            http_status_code=502,
            provider_health_status="degraded",
        )

    return GatewayErrorInfo(
        error_type="unknown",
        detail=text,
        http_status_code=502,
        provider_health_status="degraded",
    )


def normalize_gateway_error(error: Exception | GatewayErrorInfo | str) -> GatewayErrorInfo:
    if isinstance(error, GatewayErrorInfo):
        return error
    if isinstance(error, GatewayProviderError):
        return error.error
    if isinstance(error, Exception):
        return classify_gateway_error(str(error))
    return classify_gateway_error(str(error))


def gateway_error_policy(error: GatewayErrorInfo) -> GatewayErrorPolicy:
    error_type = error.error_type
    if error_type == "rate_limited":
        return GatewayErrorPolicy(
            error_type=error_type,
            retry_same_provider_sync=False,
            cooldown_mode="rate_limit",
        )
    if error_type == "stream_interrupted":
        return GatewayErrorPolicy(
            error_type=error_type,
            retry_same_provider_sync=True,
            cooldown_mode="short",
        )
    if error_type in {"upstream_timeout", "upstream_unreachable"}:
        return GatewayErrorPolicy(
            error_type=error_type,
            retry_same_provider_sync=False,
            cooldown_mode="threshold",
        )
    if error_type in {"provider_disabled", "provider_cooldown", "misconfigured"}:
        return GatewayErrorPolicy(
            error_type=error_type,
            retry_same_provider_sync=False,
            cooldown_mode="none",
        )
    return GatewayErrorPolicy(
        error_type=error_type,
        retry_same_provider_sync=False,
        cooldown_mode="threshold",
    )
