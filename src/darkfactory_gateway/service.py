from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Iterator

from darkfactory.models import Message, Project, Session
from darkfactory.services import AssistantService

from .models import (
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayProviderHealthResponse,
    GatewayRequestInfo,
)
from .registry import ProviderRecord, ProviderRegistry
from .skills import SkillRegistry


@dataclass(slots=True)
class RequestState:
    request_id: str
    client_request_id: str = ""
    canceled: bool = False
    status: str = "created"
    provider_id: str = ""
    attempted_provider_ids: list[str] | None = None
    skill_ids: list[str] | None = None
    error_detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "client_request_id": self.client_request_id,
            "status": self.status,
            "provider_id": self.provider_id,
            "attempted_provider_ids": list(self.attempted_provider_ids or []),
            "skill_ids": list(self.skill_ids or []),
            "error_detail": self.error_detail,
        }


class RequestTracker:
    def __init__(self) -> None:
        self._states: dict[str, RequestState] = {}
        self._history: list[RequestState] = []

    def create(self, client_request_id: str = "", skill_ids: list[str] | None = None) -> str:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        self._states[request_id] = RequestState(
            request_id=request_id,
            client_request_id=client_request_id,
            skill_ids=list(skill_ids or []),
        )
        return request_id

    def cancel(self, request_id: str) -> bool:
        state = self._states.get(request_id)
        if state is None:
            return False
        state.canceled = True
        state.status = "cancel_requested"
        return True

    def is_canceled(self, request_id: str) -> bool:
        state = self._states.get(request_id)
        return state.canceled if state else False

    def mark_provider_attempt(
        self,
        request_id: str,
        provider_id: str,
        attempted_provider_ids: list[str],
    ) -> None:
        state = self._states.get(request_id)
        if state is None:
            return
        state.provider_id = provider_id
        state.attempted_provider_ids = list(attempted_provider_ids)
        state.status = "running"

    def mark_error(
        self,
        request_id: str,
        *,
        provider_id: str,
        attempted_provider_ids: list[str],
        detail: str,
    ) -> None:
        state = self._states.get(request_id)
        if state is None:
            return
        state.provider_id = provider_id
        state.attempted_provider_ids = list(attempted_provider_ids)
        state.error_detail = detail
        state.status = "error"

    def mark_done(
        self,
        request_id: str,
        *,
        provider_id: str,
        attempted_provider_ids: list[str],
    ) -> None:
        state = self._states.get(request_id)
        if state is None:
            return
        state.provider_id = provider_id
        state.attempted_provider_ids = list(attempted_provider_ids)
        state.status = "completed"

    def list_recent(self, limit: int = 50) -> list[RequestState]:
        active = list(self._states.values())
        history = self._history[-limit:]
        combined = history + active
        deduped: dict[str, RequestState] = {}
        for item in combined:
            deduped[item.request_id] = item
        return list(deduped.values())[-limit:]

    def get(self, request_id: str) -> RequestState | None:
        state = self._states.get(request_id)
        if state is not None:
            return state
        for item in reversed(self._history):
            if item.request_id == request_id:
                return item
        return None

    def complete(self, request_id: str) -> None:
        state = self._states.pop(request_id, None)
        if state is not None:
            self._history.append(state)
            self._history = self._history[-200:]


class GatewayService:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry()
        self.skill_registry = skill_registry or SkillRegistry()
        self.request_tracker = RequestTracker()

    def health(self) -> dict[str, str]:
        return {
            "status": "ok",
            "provider_count": len(self.provider_registry.enabled()),
            "default_provider_id": self.provider_registry.default_provider_id(),
        }

    def list_providers(self):
        return self.provider_registry.infos()

    def list_skills(self):
        return self.skill_registry.infos()

    def list_requests(self) -> list[GatewayRequestInfo]:
        return [
            GatewayRequestInfo(**item.as_dict())
            for item in self.request_tracker.list_recent()
        ]

    def get_request(self, request_id: str) -> GatewayRequestInfo | None:
        state = self.request_tracker.get(request_id)
        if state is None:
            return None
        return GatewayRequestInfo(**state.as_dict())

    def provider_health(self, provider_id: str) -> GatewayProviderHealthResponse:
        provider = self.provider_registry.get(provider_id)
        assistant = AssistantService(provider.settings)
        try:
            detail = assistant.health_check(provider.settings)
        except Exception as exc:
            return GatewayProviderHealthResponse(
                provider_id=provider.id,
                status="error",
                detail=str(exc),
            )
        return GatewayProviderHealthResponse(
            provider_id=provider.id,
            status="ok",
            detail=detail,
        )

    def chat(self, request: GatewayChatRequest) -> GatewayChatResponse:
        providers = self.provider_registry.resolve_chain(
            provider_id=request.provider_id,
            strategy=request.provider_strategy,
        )
        request_id = self.request_tracker.create(
            client_request_id=request.client_request_id,
            skill_ids=request.skill_ids,
        )
        attempted_provider_ids: list[str] = []
        final_provider: ProviderRecord | None = None
        assistant: AssistantService | None = None
        reply = ""
        last_error: Exception | None = None

        try:
            for provider in providers:
                attempted_provider_ids.append(provider.id)
                self.request_tracker.mark_provider_attempt(
                    request_id,
                    provider.id,
                    attempted_provider_ids,
                )
                assistant = AssistantService(provider.settings)
                project, session, recent_messages, user_message = self._to_domain_inputs(
                    request,
                    provider,
                )
                try:
                    reply = "".join(
                        assistant.stream_reply(
                            project=project,
                            session=session,
                            recent_messages=recent_messages,
                            user_message=user_message,
                            settings=provider.settings,
                            client_request_id=request_id,
                        )
                    )
                    final_provider = provider
                    self.request_tracker.mark_done(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        detail=str(exc),
                    )
                    if request.provider_strategy != "fallback":
                        raise

            if final_provider is None or assistant is None:
                raise RuntimeError(str(last_error) if last_error else "No provider resolved")

            metrics = assistant.last_response_metrics()
            return GatewayChatResponse(
                request_id=request_id,
                client_request_id=request.client_request_id,
                provider_id=final_provider.id,
                attempted_provider_ids=attempted_provider_ids,
                reply=reply,
                stream_mode=metrics.stream_mode,
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
                total_tokens=metrics.total_tokens,
            )
        finally:
            self.request_tracker.complete(request_id)

    def stream_chat(self, request: GatewayChatRequest) -> Iterator[str]:
        request_id = self.request_tracker.create(
            client_request_id=request.client_request_id,
            skill_ids=request.skill_ids,
        )
        providers = self.provider_registry.resolve_chain(
            provider_id=request.provider_id,
            strategy=request.provider_strategy,
        )
        attempted_provider_ids: list[str] = []

        try:
            for provider in providers:
                attempted_provider_ids.append(provider.id)
                self.request_tracker.mark_provider_attempt(
                    request_id,
                    provider.id,
                    attempted_provider_ids,
                )
                project, session, recent_messages, user_message = self._to_domain_inputs(
                    request,
                    provider,
                )
                assistant = AssistantService(provider.settings)
                yield self._sse(
                    {
                        "type": "request",
                        "request_id": request_id,
                        "client_request_id": request.client_request_id,
                        "provider_id": provider.id,
                        "attempted_provider_ids": attempted_provider_ids,
                    }
                )
                try:
                    for chunk in assistant.stream_reply(
                        project=project,
                        session=session,
                        recent_messages=recent_messages,
                        user_message=user_message,
                        settings=provider.settings,
                        client_request_id=request_id,
                    ):
                        if self.request_tracker.is_canceled(request_id):
                            yield self._sse({"type": "canceled", "request_id": request_id})
                            return
                        if not chunk:
                            continue
                        yield self._sse({"type": "delta", "delta": chunk})
                    metrics = assistant.last_response_metrics()
                    if metrics.total_tokens:
                        yield self._sse(
                            {
                                "type": "usage",
                                "prompt_tokens": metrics.prompt_tokens,
                                "completion_tokens": metrics.completion_tokens,
                                "total_tokens": metrics.total_tokens,
                            }
                        )
                    yield self._sse(
                        {
                            "type": "done",
                            "request_id": request_id,
                            "client_request_id": request.client_request_id,
                            "provider_id": provider.id,
                            "attempted_provider_ids": attempted_provider_ids,
                        }
                    )
                    self.request_tracker.mark_done(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                    )
                    return
                except Exception as exc:
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        detail=str(exc),
                    )
                    if request.provider_strategy != "fallback":
                        raise
                    yield self._sse(
                        {
                            "type": "provider_error",
                            "request_id": request_id,
                            "provider_id": provider.id,
                            "detail": str(exc),
                        }
                    )
            raise RuntimeError("All configured providers failed for the request")
        finally:
            self.request_tracker.complete(request_id)

    def cancel(self, request_id: str) -> str:
        if self.request_tracker.cancel(request_id):
            return "cancel_requested"
        return "unknown_request"

    def _to_domain_inputs(
        self,
        request: GatewayChatRequest,
        provider: ProviderRecord,
    ) -> tuple[Project, Session, list[Message], str]:
        rendered_skills = self.skill_registry.resolve(
            request=request,
            default_skill_ids=provider.normalized_default_skill_ids(),
        )
        user_message = self._compose_user_message(request.message, rendered_skills)

        project = Project(
            id=request.project.id,
            name=request.project.name,
            plant=request.project.plant,
            unit=request.project.unit,
            expert_type=request.project.expert_type,
            created_at=request.project.created_at,
        )
        session = Session(
            id=request.session.id,
            project_id=request.session.project_id,
            name=request.session.name,
            summary=request.session.summary,
            updated_at=request.session.updated_at,
        )
        recent_messages = [
            Message(
                id=item.id,
                session_id=item.session_id,
                role=item.role,
                content=item.content,
                created_at=item.created_at,
            )
            for item in request.recent_messages
        ]
        return project, session, recent_messages, user_message

    def _compose_user_message(self, message: str, rendered_skills: list) -> str:
        if not rendered_skills:
            return message

        skill_blocks = [
            f"[{skill.id}] {skill.content}"
            for skill in rendered_skills
        ]
        return (
            "[Gateway Skills]\n"
            + "\n".join(skill_blocks)
            + "\n\n[User Message]\n"
            + message
        )

    def _sse(self, data: dict[str, object]) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
