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
