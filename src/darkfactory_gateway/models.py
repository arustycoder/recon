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
    provider_id: str | None = None
    skill_ids: list[str] = Field(default_factory=list)


class GatewayChatResponse(BaseModel):
    request_id: str
    provider_id: str
    reply: str
    stream_mode: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GatewayProviderInfo(BaseModel):
    id: str
    kind: str
    label: str
    default: bool = False


class GatewaySkillInfo(BaseModel):
    id: str
    label: str
    description: str


class GatewayHealthResponse(BaseModel):
    status: Literal["ok"]


class GatewayCancelResponse(BaseModel):
    request_id: str
    status: str
