from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Project:
    id: int
    name: str
    plant: str
    unit: str
    expert_type: str
    created_at: str


@dataclass(slots=True)
class Session:
    id: int
    project_id: int
    name: str
    summary: str
    updated_at: str


@dataclass(slots=True)
class Message:
    id: int
    session_id: int
    role: str
    content: str
    created_at: str


@dataclass(slots=True)
class ProviderSettings:
    provider: str = "mock"
    ollama_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = ""
    ollama_api_key: str = "ollama"
    openai_base_url: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    api_url: str = ""
    api_health_url: str = ""
    api_stream_url: str = ""
    api_cancel_url_template: str = ""
    api_providers_url: str = ""
    request_timeout_seconds: int = 60


@dataclass(slots=True)
class RequestLog:
    id: int
    session_id: int | None
    provider: str
    model: str
    status: str
    stream_mode: str
    latency_ms: int
    first_token_latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    detail: str
    created_at: str


@dataclass(slots=True)
class GatewayRequestRecord:
    request_id: str
    client_request_id: str
    session_id: int | None
    status: str
    phase: str
    provider_id: str
    target: str
    stream_mode: str
    latency_ms: int
    first_token_latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    attempted_provider_ids: str
    skill_ids: str
    error_detail: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class ResponseMetrics:
    stream_mode: str = ""
    latency_ms: int = 0
    first_token_latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
