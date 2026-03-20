from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

from darkfactory.models import Message, Project, Session
from darkfactory.services import AssistantService
from darkfactory.storage import Storage

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
    session_id: int | None = None
    canceled: bool = False
    status: str = "created"
    phase: str = "created"
    provider_id: str = ""
    attempted_provider_ids: list[str] | None = None
    skill_ids: list[str] | None = None
    error_detail: str = ""
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "client_request_id": self.client_request_id,
            "session_id": self.session_id,
            "status": self.status,
            "phase": self.phase,
            "provider_id": self.provider_id,
            "attempted_provider_ids": list(self.attempted_provider_ids or []),
            "skill_ids": list(self.skill_ids or []),
            "error_detail": self.error_detail,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class ProviderCircuitState:
    consecutive_failures: int = 0
    cooldown_until: float = 0.0


class RequestTracker:
    def __init__(self) -> None:
        self._states: dict[str, RequestState] = {}
        self._history: list[RequestState] = []

    def create(
        self,
        client_request_id: str = "",
        skill_ids: list[str] | None = None,
        session_id: int | None = None,
    ) -> str:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        now = self._timestamp()
        self._states[request_id] = RequestState(
            request_id=request_id,
            client_request_id=client_request_id,
            session_id=session_id,
            skill_ids=list(skill_ids or []),
            created_at=now,
            updated_at=now,
        )
        return request_id

    def cancel(self, request_id: str) -> bool:
        state = self._states.get(request_id)
        if state is None:
            return False
        state.canceled = True
        state.status = "cancel_requested"
        state.phase = "canceled"
        state.updated_at = self._timestamp()
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
        state.phase = "provider_routing"
        state.updated_at = self._timestamp()

    def mark_phase(self, request_id: str, phase: str) -> None:
        state = self._states.get(request_id)
        if state is None:
            return
        state.phase = phase
        state.updated_at = self._timestamp()

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
        state.phase = "error"
        state.updated_at = self._timestamp()

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
        state.phase = "completed"
        state.updated_at = self._timestamp()

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

    def _timestamp(self) -> str:
        return datetime.now().isoformat(timespec="seconds")


class GatewayService:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
        storage: Storage | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry()
        self.skill_registry = skill_registry or SkillRegistry()
        self.request_tracker = RequestTracker()
        self.storage = storage or Storage()
        self._provider_circuits: dict[str, ProviderCircuitState] = {}

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
            self._record_to_request_info(record)
            for record in self.storage.list_gateway_requests()
        ]

    def get_request(self, request_id: str) -> GatewayRequestInfo | None:
        record = self.storage.get_gateway_request(request_id)
        if record is None:
            return None
        return self._record_to_request_info(record)

    def provider_health(self, provider_id: str) -> GatewayProviderHealthResponse:
        provider = self.provider_registry.get(provider_id)
        circuit = self._provider_circuits.get(provider.id, ProviderCircuitState())
        remaining = max(0, int(circuit.cooldown_until - time.time()))
        if remaining > 0:
            return GatewayProviderHealthResponse(
                provider_id=provider.id,
                status="error",
                detail=f"Provider is cooling down for {remaining}s",
            )
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
            session_id=request.session.id,
        )
        self._persist_request_state(request_id)
        attempted_provider_ids: list[str] = []
        final_provider: ProviderRecord | None = None
        assistant: AssistantService | None = None
        reply = ""
        last_error: Exception | None = None

        try:
            for provider in self._filter_provider_chain(providers):
                selected_skills, pre_context_skills, prompt_skills, post_skills = self._prepare_skills(
                    request,
                    provider,
                )
                attempted_provider_ids.append(provider.id)
                self.request_tracker.mark_provider_attempt(
                    request_id,
                    provider.id,
                    attempted_provider_ids,
                )
                self._persist_request_state(request_id)
                cooldown_remaining = self._provider_cooldown_remaining(provider.id)
                if cooldown_remaining > 0:
                    detail = f"Provider is cooling down for {cooldown_remaining}s"
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        detail=detail,
                    )
                    self._persist_request_state(request_id)
                    last_error = RuntimeError(detail)
                    if request.provider_strategy != "fallback":
                        raise last_error
                    continue
                assistant = AssistantService(provider.settings)
                project, session, recent_messages, user_message = self._to_domain_inputs(
                    request,
                    pre_context_skills=pre_context_skills,
                    prompt_skills=prompt_skills,
                )
                try:
                    self.request_tracker.mark_phase(request_id, "model_execution")
                    self._persist_request_state(request_id)
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
                    if post_skills:
                        self.request_tracker.mark_phase(request_id, "post_processing")
                        self._persist_request_state(request_id)
                        reply = self.skill_registry.apply_post_processing(
                            request=request,
                            selected_skills=selected_skills,
                            reply=reply,
                        )
                    final_provider = provider
                    self._record_provider_success(provider.id)
                    self.request_tracker.mark_done(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                    )
                    self._persist_request_state(request_id)
                    break
                except Exception as exc:
                    last_error = exc
                    self._record_provider_failure(provider.id, provider)
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        detail=str(exc),
                    )
                    self._persist_request_state(request_id)
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
            session_id=request.session.id,
        )
        self._persist_request_state(request_id)
        providers = self.provider_registry.resolve_chain(
            provider_id=request.provider_id,
            strategy=request.provider_strategy,
        )
        attempted_provider_ids: list[str] = []

        try:
            for provider in self._filter_provider_chain(providers):
                selected_skills, pre_context_skills, prompt_skills, post_skills = self._prepare_skills(
                    request,
                    provider,
                )
                attempted_provider_ids.append(provider.id)
                self.request_tracker.mark_provider_attempt(
                    request_id,
                    provider.id,
                    attempted_provider_ids,
                )
                self._persist_request_state(request_id)
                cooldown_remaining = self._provider_cooldown_remaining(provider.id)
                if cooldown_remaining > 0:
                    detail = f"Provider is cooling down for {cooldown_remaining}s"
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        detail=detail,
                    )
                    self._persist_request_state(request_id)
                    if request.provider_strategy != "fallback":
                        raise RuntimeError(detail)
                    yield self._sse(
                        {
                            "type": "provider_error",
                            "request_id": request_id,
                            "provider_id": provider.id,
                            "detail": detail,
                        }
                    )
                    continue
                project, session, recent_messages, user_message = self._to_domain_inputs(
                    request,
                    pre_context_skills=pre_context_skills,
                    prompt_skills=prompt_skills,
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
                    self.request_tracker.mark_phase(request_id, "model_execution")
                    self._persist_request_state(request_id)
                    buffered_chunks: list[str] = []
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
                        if post_skills:
                            buffered_chunks.append(chunk)
                            continue
                        yield self._sse({"type": "delta", "delta": chunk})
                    if post_skills:
                        self.request_tracker.mark_phase(request_id, "post_processing")
                        self._persist_request_state(request_id)
                        processed_reply = self.skill_registry.apply_post_processing(
                            request=request,
                            selected_skills=selected_skills,
                            reply="".join(buffered_chunks),
                        )
                        yield self._sse({"type": "delta", "delta": processed_reply})
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
                    self._record_provider_success(provider.id)
                    self.request_tracker.mark_done(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                    )
                    self._persist_request_state(request_id)
                    return
                except Exception as exc:
                    self._record_provider_failure(provider.id, provider)
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        detail=str(exc),
                    )
                    self._persist_request_state(request_id)
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
            self._persist_request_state(request_id)
            return "cancel_requested"
        return "unknown_request"

    def _to_domain_inputs(
        self,
        request: GatewayChatRequest,
        *,
        pre_context_skills: list,
        prompt_skills: list,
    ) -> tuple[Project, Session, list[Message], str]:
        user_message = self._compose_user_message(
            request.message,
            pre_context_skills=pre_context_skills,
            prompt_skills=prompt_skills,
        )

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

    def _prepare_skills(
        self,
        request: GatewayChatRequest,
        provider: ProviderRecord,
    ) -> tuple[list, list, list, list]:
        selected_skills = self.skill_registry.select(
            request=request,
            default_skill_ids=provider.normalized_default_skill_ids(),
        )
        pre_context_skills = self.skill_registry.render_phase(
            request=request,
            selected_skills=selected_skills,
            phase="pre_context",
        )
        prompt_skills = self.skill_registry.render_phase(
            request=request,
            selected_skills=selected_skills,
            phase="prompt_shaping",
        )
        post_skills = [
            skill
            for skill in selected_skills
            if skill.phase == "post_processing"
        ]
        return selected_skills, pre_context_skills, prompt_skills, post_skills

    def _compose_user_message(
        self,
        message: str,
        *,
        pre_context_skills: list,
        prompt_skills: list,
    ) -> str:
        if not pre_context_skills and not prompt_skills:
            return message

        parts: list[str] = []
        if pre_context_skills:
            parts.append(
                "[Gateway Context]\n"
                + "\n".join(f"[{skill.id}] {skill.content}" for skill in pre_context_skills)
            )
        if prompt_skills:
            parts.append(
                "[Gateway Prompt]\n"
                + "\n".join(f"[{skill.id}] {skill.content}" for skill in prompt_skills)
            )
        parts.append("[User Message]\n" + message)
        return "\n\n".join(parts)

    def _persist_request_state(self, request_id: str) -> None:
        state = self.request_tracker.get(request_id)
        if state is None:
            return
        self.storage.save_gateway_request(
            request_id=state.request_id,
            client_request_id=state.client_request_id,
            session_id=state.session_id,
            status=state.status,
            phase=state.phase,
            provider_id=state.provider_id,
            attempted_provider_ids=list(state.attempted_provider_ids or []),
            skill_ids=list(state.skill_ids or []),
            error_detail=state.error_detail,
        )

    def _record_to_request_info(self, record) -> GatewayRequestInfo:
        return GatewayRequestInfo(
            request_id=record.request_id,
            client_request_id=record.client_request_id,
            status=record.status,
            phase=record.phase,
            provider_id=record.provider_id,
            attempted_provider_ids=json.loads(record.attempted_provider_ids or "[]"),
            skill_ids=json.loads(record.skill_ids or "[]"),
            error_detail=record.error_detail,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _filter_provider_chain(self, providers: list[ProviderRecord]) -> list[ProviderRecord]:
        available: list[ProviderRecord] = []
        blocked: list[ProviderRecord] = []
        now = time.time()
        for provider in providers:
            state = self._provider_circuits.get(provider.id, ProviderCircuitState())
            if state.cooldown_until > now:
                blocked.append(provider)
                continue
            available.append(provider)
        return available or blocked

    def _record_provider_success(self, provider_id: str) -> None:
        self._provider_circuits[provider_id] = ProviderCircuitState()

    def _record_provider_failure(self, provider_id: str, provider: ProviderRecord) -> None:
        state = self._provider_circuits.get(provider_id, ProviderCircuitState())
        state.consecutive_failures += 1
        if state.consecutive_failures >= provider.max_consecutive_failures:
            state.cooldown_until = time.time() + provider.cooldown_seconds
        self._provider_circuits[provider_id] = state

    def _provider_cooldown_remaining(self, provider_id: str) -> int:
        state = self._provider_circuits.get(provider_id, ProviderCircuitState())
        return max(0, int(state.cooldown_until - time.time()))

    def _sse(self, data: dict[str, object]) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
