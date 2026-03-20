from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GatewayProject(BaseModel):
    id: int
    name: str
    plant: str = ""
    unit: str = ""
    expert_type: str = ""
    created_at: str = ""


class GatewaySession(BaseModel):
    id: int
    project_id: int
    name: str
    summary: str = ""
    updated_at: str = ""


class GatewayMessage(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: str = ""


class GatewayChatRequest(BaseModel):
    project: GatewayProject
    session: GatewaySession
    recent_messages: list[GatewayMessage] = Field(default_factory=list)
    message: str
    client_request_id: str = ""
    provider_id: str | None = None
    provider_strategy: Literal["default", "fallback"] = "default"
    skill_ids: list[str] = Field(default_factory=list)
    skill_mode: Literal["merge", "request_only"] = "merge"
    skill_arguments: dict[str, dict[str, str]] = Field(default_factory=dict)


class GatewayChatResponse(BaseModel):
    request_id: str
    client_request_id: str = ""
    provider_id: str
    target: str = ""
    reply: str
    attempted_provider_ids: list[str] = Field(default_factory=list)
    stream_mode: str = ""
    latency_ms: int = 0
    first_token_latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class GatewayProviderInfo(BaseModel):
    id: str
    kind: str
    label: str
    default: bool = False
    enabled: bool = True
    priority: int = 100
    tags: list[str] = Field(default_factory=list)
    default_skill_ids: list[str] = Field(default_factory=list)
    cooldown_seconds: int = 0
    max_consecutive_failures: int = 0
    prompt_cost_per_1k: float = 0.0
    completion_cost_per_1k: float = 0.0


class GatewaySkillInfo(BaseModel):
    id: str
    label: str
    description: str
    phase: str = "prompt_shaping"
    enabled_by_default: bool = False
    parameter_keys: list[str] = Field(default_factory=list)


class GatewayHealthResponse(BaseModel):
    status: Literal["ok"]
    provider_count: int = 0
    default_provider_id: str = ""


class GatewayCancelResponse(BaseModel):
    request_id: str
    status: str


class GatewayProviderHealthResponse(BaseModel):
    provider_id: str
    status: Literal["healthy", "degraded", "cooldown", "disabled", "misconfigured", "unreachable"]
    detail: str
    consecutive_failures: int = 0
    cooldown_remaining_seconds: int = 0


class GatewayProviderResetResponse(BaseModel):
    provider_id: str
    status: Literal["reset"]


class GatewayRequestInfo(BaseModel):
    request_id: str
    client_request_id: str = ""
    status: str
    phase: str = ""
    provider_id: str = ""
    target: str = ""
    stream_mode: str = ""
    latency_ms: int = 0
    first_token_latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    attempted_provider_ids: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    error_detail: str = ""
    created_at: str = ""
    updated_at: str = ""


class GatewayRequestSummaryGroup(BaseModel):
    key: str
    request_count: int = 0
    completed_count: int = 0
    error_count: int = 0
    avg_latency_ms: int = 0
    avg_first_token_latency_ms: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class GatewayRequestSummaryResponse(BaseModel):
    request_count: int = 0
    completed_count: int = 0
    error_count: int = 0
    avg_latency_ms: int = 0
    avg_first_token_latency_ms: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    by_provider: list[GatewayRequestSummaryGroup] = Field(default_factory=list)
    by_status: list[GatewayRequestSummaryGroup] = Field(default_factory=list)
