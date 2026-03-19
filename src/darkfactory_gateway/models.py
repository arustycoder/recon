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
    reply: str
    attempted_provider_ids: list[str] = Field(default_factory=list)
    stream_mode: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GatewayProviderInfo(BaseModel):
    id: str
    kind: str
    label: str
    default: bool = False
    enabled: bool = True
    priority: int = 100
    tags: list[str] = Field(default_factory=list)
    default_skill_ids: list[str] = Field(default_factory=list)


class GatewaySkillInfo(BaseModel):
    id: str
    label: str
    description: str
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
    status: Literal["ok", "error"]
    detail: str


class GatewayRequestInfo(BaseModel):
    request_id: str
    client_request_id: str = ""
    status: str
    provider_id: str = ""
    attempted_provider_ids: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    error_detail: str = ""
