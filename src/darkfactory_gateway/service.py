from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

from darkfactory.models import Message, Project, ResponseMetrics, Session
from darkfactory.storage import Storage

from .adapters import GatewayAdapterFactory, GatewayProviderAdapter
from .errors import GatewayErrorInfo, classify_gateway_error
from .models import (
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayProviderHealthResponse,
    GatewayProviderResetResponse,
    GatewayRequestInfo,
    GatewayRequestSummaryGroup,
    GatewayRequestSummaryResponse,
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
    target: str = ""
    stream_mode: str = ""
    latency_ms: int = 0
    first_token_latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    attempted_provider_ids: list[str] | None = None
    skill_ids: list[str] | None = None
    error_type: str = ""
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
            "target": self.target,
            "stream_mode": self.stream_mode,
            "latency_ms": self.latency_ms,
            "first_token_latency_ms": self.first_token_latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "attempted_provider_ids": list(self.attempted_provider_ids or []),
            "skill_ids": list(self.skill_ids or []),
            "error_type": self.error_type,
            "error_detail": self.error_detail,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class ProviderCircuitState:
    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    reason: str = ""
    last_error_type: str = ""
    last_error_detail: str = ""


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
        target: str = "",
    ) -> None:
        state = self._states.get(request_id)
        if state is None:
            return
        state.provider_id = provider_id
        state.target = target
        state.attempted_provider_ids = list(attempted_provider_ids)
        state.status = "running"
        state.phase = "provider_routing"
        state.updated_at = self._timestamp()

    def apply_metrics(
        self,
        request_id: str,
        *,
        target: str,
        metrics: ResponseMetrics,
        estimated_cost_usd: float,
    ) -> None:
        state = self._states.get(request_id)
        if state is None:
            return
        state.target = target
        state.stream_mode = metrics.stream_mode
        state.latency_ms = metrics.latency_ms
        state.first_token_latency_ms = metrics.first_token_latency_ms
        state.prompt_tokens = metrics.prompt_tokens
        state.completion_tokens = metrics.completion_tokens
        state.total_tokens = metrics.total_tokens
        state.estimated_cost_usd = round(estimated_cost_usd, 6)
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
        error: GatewayErrorInfo,
    ) -> None:
        state = self._states.get(request_id)
        if state is None:
            return
        state.provider_id = provider_id
        state.attempted_provider_ids = list(attempted_provider_ids)
        state.error_type = error.error_type
        state.error_detail = error.detail
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
        adapter_factory: GatewayAdapterFactory | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry()
        self.skill_registry = skill_registry or SkillRegistry()
        self.request_tracker = RequestTracker()
        self.storage = storage or Storage()
        self.adapter_factory = adapter_factory or GatewayAdapterFactory()
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

    def list_requests(
        self,
        *,
        provider_id: str = "",
        status: str = "",
        phase: str = "",
        since_minutes: int = 0,
        limit: int = 100,
    ) -> list[GatewayRequestInfo]:
        return [
            self._record_to_request_info(record)
            for record in self.storage.filter_gateway_requests(
                limit=limit,
                provider_id=provider_id,
                status=status,
                phase=phase,
                since_minutes=since_minutes,
            )
        ]

    def request_summary(
        self,
        *,
        provider_id: str = "",
        status: str = "",
        phase: str = "",
        since_minutes: int = 0,
    ) -> GatewayRequestSummaryResponse:
        records = self.storage.filter_gateway_requests(
            limit=1000,
            provider_id=provider_id,
            status=status,
            phase=phase,
            since_minutes=since_minutes,
        )
        return GatewayRequestSummaryResponse(
            request_count=len(records),
            completed_count=sum(1 for item in records if item.status == "completed"),
            error_count=sum(1 for item in records if item.status == "error"),
            avg_latency_ms=self._average_int(
                item.latency_ms for item in records if item.latency_ms > 0
            ),
            avg_first_token_latency_ms=self._average_int(
                item.first_token_latency_ms for item in records if item.first_token_latency_ms > 0
            ),
            total_tokens=sum(item.total_tokens for item in records),
            estimated_cost_usd=round(sum(item.estimated_cost_usd for item in records), 6),
            by_provider=self._summarize_groups(records, "provider_id"),
            by_status=self._summarize_groups(records, "status"),
            by_error_type=self._summarize_groups(records, "error_type"),
        )

    def get_request(self, request_id: str) -> GatewayRequestInfo | None:
        record = self.storage.get_gateway_request(request_id)
        if record is None:
            return None
        return self._record_to_request_info(record)

    def provider_health(self, provider_id: str) -> GatewayProviderHealthResponse:
        provider = self.provider_registry.get(provider_id)
        circuit = self._provider_circuits.get(provider.id, ProviderCircuitState())
        remaining = self._provider_cooldown_remaining(provider.id)
        if not provider.enabled:
            error = classify_gateway_error("Provider is disabled in registry")
            return GatewayProviderHealthResponse(
                provider_id=provider.id,
                status=error.provider_health_status,
                detail=error.detail,
                consecutive_failures=circuit.consecutive_failures,
                cooldown_remaining_seconds=0,
                last_error_type=circuit.last_error_type or error.error_type,
                last_error_detail=circuit.last_error_detail or error.detail,
            )
        if remaining > 0:
            error = self._cooldown_error(circuit, remaining)
            return GatewayProviderHealthResponse(
                provider_id=provider.id,
                status=error.provider_health_status,
                detail=error.detail,
                consecutive_failures=circuit.consecutive_failures,
                cooldown_remaining_seconds=remaining,
                last_error_type=circuit.last_error_type,
                last_error_detail=circuit.last_error_detail,
            )
        misconfigured = self._provider_misconfiguration(provider)
        if misconfigured:
            error = classify_gateway_error(misconfigured)
            return GatewayProviderHealthResponse(
                provider_id=provider.id,
                status=error.provider_health_status,
                detail=error.detail,
                consecutive_failures=circuit.consecutive_failures,
                cooldown_remaining_seconds=0,
                last_error_type=error.error_type,
                last_error_detail=error.detail,
            )

        adapter = self.adapter_factory.create(provider.settings)
        try:
            detail = adapter.health_check()
        except Exception as exc:
            error = classify_gateway_error(str(exc))
            return GatewayProviderHealthResponse(
                provider_id=provider.id,
                status=error.provider_health_status,
                detail=error.detail,
                consecutive_failures=circuit.consecutive_failures,
                cooldown_remaining_seconds=0,
                last_error_type=error.error_type,
                last_error_detail=error.detail,
            )
        status = "degraded" if circuit.consecutive_failures > 0 else "healthy"
        return GatewayProviderHealthResponse(
            provider_id=provider.id,
            status=status,
            detail=detail,
            consecutive_failures=circuit.consecutive_failures,
            cooldown_remaining_seconds=0,
            last_error_type=circuit.last_error_type,
            last_error_detail=circuit.last_error_detail,
        )

    def reset_provider(self, provider_id: str) -> GatewayProviderResetResponse:
        self.provider_registry.get(provider_id)
        self._provider_circuits[provider_id] = ProviderCircuitState()
        return GatewayProviderResetResponse(provider_id=provider_id, status="reset")

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
        adapter: GatewayProviderAdapter | None = None
        reply = ""
        last_error: Exception | None = None

        try:
            for provider in self._filter_provider_chain(providers):
                selected_skills, pre_context_skills, prompt_skills, post_skills = self._prepare_skills(
                    request,
                    provider,
                )
                adapter = self.adapter_factory.create(provider.settings)
                attempted_provider_ids.append(provider.id)
                self.request_tracker.mark_provider_attempt(
                    request_id,
                    provider.id,
                    attempted_provider_ids,
                    target=adapter.target_label(),
                )
                self._persist_request_state(request_id)
                if not provider.enabled:
                    error = classify_gateway_error("Provider is disabled in registry")
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        error=error,
                    )
                    self._persist_request_state(request_id)
                    last_error = RuntimeError(error.detail)
                    if request.provider_strategy != "fallback":
                        raise last_error
                    continue
                cooldown_remaining = self._provider_cooldown_remaining(provider.id)
                if cooldown_remaining > 0:
                    circuit = self._provider_circuits.get(provider.id, ProviderCircuitState())
                    error = self._cooldown_error(circuit, cooldown_remaining)
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        error=error,
                    )
                    self._persist_request_state(request_id)
                    last_error = RuntimeError(error.detail)
                    if request.provider_strategy != "fallback":
                        raise last_error
                    continue
                project, session, recent_messages, user_message = self._to_domain_inputs(
                    request,
                    pre_context_skills=pre_context_skills,
                    prompt_skills=prompt_skills,
                )
                try:
                    self.request_tracker.mark_phase(request_id, "model_execution")
                    self._persist_request_state(request_id)
                    reply = adapter.reply(
                        project=project,
                        session=session,
                        recent_messages=recent_messages,
                        user_message=user_message,
                        client_request_id=request_id,
                    )
                    if post_skills:
                        self.request_tracker.mark_phase(request_id, "post_processing")
                        self._persist_request_state(request_id)
                        reply = self.skill_registry.apply_post_processing(
                            request=request,
                            selected_skills=selected_skills,
                            reply=reply,
                        )
                    adapter_result = adapter.last_result()
                    estimated_cost = self._estimate_cost_usd(
                        provider,
                        adapter_result.metrics,
                    )
                    self.request_tracker.apply_metrics(
                        request_id,
                        target=adapter_result.target,
                        metrics=adapter_result.metrics,
                        estimated_cost_usd=estimated_cost,
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
                    error = classify_gateway_error(str(exc))
                    self._record_provider_failure(provider.id, provider, error)
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        error=error,
                    )
                    self._persist_request_state(request_id)
                    if request.provider_strategy != "fallback":
                        raise RuntimeError(error.detail) from exc

            if final_provider is None or adapter is None:
                raise RuntimeError(str(last_error) if last_error else "No provider resolved")

            adapter_result = adapter.last_result()
            return GatewayChatResponse(
                request_id=request_id,
                client_request_id=request.client_request_id,
                provider_id=final_provider.id,
                target=adapter_result.target,
                attempted_provider_ids=attempted_provider_ids,
                reply=reply,
                stream_mode=adapter_result.metrics.stream_mode,
                latency_ms=adapter_result.metrics.latency_ms,
                first_token_latency_ms=adapter_result.metrics.first_token_latency_ms,
                prompt_tokens=adapter_result.metrics.prompt_tokens,
                completion_tokens=adapter_result.metrics.completion_tokens,
                total_tokens=adapter_result.metrics.total_tokens,
                estimated_cost_usd=self._estimate_cost_usd(final_provider, adapter_result.metrics),
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
                adapter = self.adapter_factory.create(provider.settings)
                attempted_provider_ids.append(provider.id)
                self.request_tracker.mark_provider_attempt(
                    request_id,
                    provider.id,
                    attempted_provider_ids,
                    target=adapter.target_label(),
                )
                self._persist_request_state(request_id)
                if not provider.enabled:
                    error = classify_gateway_error("Provider is disabled in registry")
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        error=error,
                    )
                    self._persist_request_state(request_id)
                    if request.provider_strategy != "fallback":
                        yield from self._stream_terminal_error(
                            request_id=request_id,
                            client_request_id=request.client_request_id,
                            provider_id=provider.id,
                            attempted_provider_ids=attempted_provider_ids,
                            error=error,
                        )
                        return
                    yield self._sse(
                        {
                            "type": "provider_error",
                            "request_id": request_id,
                            "provider_id": provider.id,
                            "error_type": error.error_type,
                            "status_code": error.http_status_code,
                            "detail": error.detail,
                        }
                    )
                    continue
                cooldown_remaining = self._provider_cooldown_remaining(provider.id)
                if cooldown_remaining > 0:
                    circuit = self._provider_circuits.get(provider.id, ProviderCircuitState())
                    error = self._cooldown_error(circuit, cooldown_remaining)
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        error=error,
                    )
                    self._persist_request_state(request_id)
                    if request.provider_strategy != "fallback":
                        yield from self._stream_terminal_error(
                            request_id=request_id,
                            client_request_id=request.client_request_id,
                            provider_id=provider.id,
                            attempted_provider_ids=attempted_provider_ids,
                            error=error,
                        )
                        return
                    yield self._sse(
                        {
                            "type": "provider_error",
                            "request_id": request_id,
                            "provider_id": provider.id,
                            "error_type": error.error_type,
                            "status_code": error.http_status_code,
                            "detail": error.detail,
                        }
                    )
                    continue
                project, session, recent_messages, user_message = self._to_domain_inputs(
                    request,
                    pre_context_skills=pre_context_skills,
                    prompt_skills=prompt_skills,
                )
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
                    for chunk in adapter.stream_reply(
                        project=project,
                        session=session,
                        recent_messages=recent_messages,
                        user_message=user_message,
                        client_request_id=request_id,
                    ):
                        if self.request_tracker.is_canceled(request_id):
                            yield self._sse({"type": "canceled", "request_id": request_id})
                            yield self._sse(
                                {
                                    "type": "done",
                                    "request_id": request_id,
                                    "client_request_id": request.client_request_id,
                                    "provider_id": provider.id,
                                    "attempted_provider_ids": attempted_provider_ids,
                                    "status": "canceled",
                                }
                            )
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
                    adapter_result = adapter.last_result()
                    estimated_cost = self._estimate_cost_usd(provider, adapter_result.metrics)
                    self.request_tracker.apply_metrics(
                        request_id,
                        target=adapter_result.target,
                        metrics=adapter_result.metrics,
                        estimated_cost_usd=estimated_cost,
                    )
                    self._persist_request_state(request_id)
                    metrics = adapter_result.metrics
                    if metrics.total_tokens:
                        yield self._sse(
                            {
                                "type": "usage",
                                "prompt_tokens": metrics.prompt_tokens,
                                "completion_tokens": metrics.completion_tokens,
                                "total_tokens": metrics.total_tokens,
                                "estimated_cost_usd": estimated_cost,
                            }
                        )
                    yield self._sse(
                        {
                            "type": "done",
                            "request_id": request_id,
                            "client_request_id": request.client_request_id,
                            "provider_id": provider.id,
                            "attempted_provider_ids": attempted_provider_ids,
                            "status": "completed",
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
                    error = classify_gateway_error(str(exc))
                    self._record_provider_failure(provider.id, provider, error)
                    self.request_tracker.mark_error(
                        request_id,
                        provider_id=provider.id,
                        attempted_provider_ids=attempted_provider_ids,
                        error=error,
                    )
                    self._persist_request_state(request_id)
                    if request.provider_strategy != "fallback":
                        yield from self._stream_terminal_error(
                            request_id=request_id,
                            client_request_id=request.client_request_id,
                            provider_id=provider.id,
                            attempted_provider_ids=attempted_provider_ids,
                            error=error,
                        )
                        return
                    yield self._sse(
                        {
                            "type": "provider_error",
                            "request_id": request_id,
                            "provider_id": provider.id,
                            "error_type": error.error_type,
                            "status_code": error.http_status_code,
                            "detail": error.detail,
                        }
                    )
            yield from self._stream_terminal_error(
                request_id=request_id,
                client_request_id=request.client_request_id,
                provider_id="",
                attempted_provider_ids=attempted_provider_ids,
                error=classify_gateway_error(
                    "All configured providers failed for the request"
                ),
            )
            return
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
            target=state.target,
            stream_mode=state.stream_mode,
            latency_ms=state.latency_ms,
            first_token_latency_ms=state.first_token_latency_ms,
            prompt_tokens=state.prompt_tokens,
            completion_tokens=state.completion_tokens,
            total_tokens=state.total_tokens,
            estimated_cost_usd=state.estimated_cost_usd,
            attempted_provider_ids=list(state.attempted_provider_ids or []),
            skill_ids=list(state.skill_ids or []),
            error_type=state.error_type,
            error_detail=state.error_detail,
        )

    def _record_to_request_info(self, record) -> GatewayRequestInfo:
        return GatewayRequestInfo(
            request_id=record.request_id,
            client_request_id=record.client_request_id,
            status=record.status,
            phase=record.phase,
            provider_id=record.provider_id,
            target=record.target,
            stream_mode=record.stream_mode,
            latency_ms=record.latency_ms,
            first_token_latency_ms=record.first_token_latency_ms,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            total_tokens=record.total_tokens,
            estimated_cost_usd=record.estimated_cost_usd,
            attempted_provider_ids=json.loads(record.attempted_provider_ids or "[]"),
            skill_ids=json.loads(record.skill_ids or "[]"),
            error_type=record.error_type,
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

    def _record_provider_failure(
        self,
        provider_id: str,
        provider: ProviderRecord,
        error: GatewayErrorInfo,
    ) -> None:
        state = self._provider_circuits.get(provider_id, ProviderCircuitState())
        state.consecutive_failures += 1
        state.last_error_type = error.error_type
        state.last_error_detail = error.detail
        if error.cooldown_reason == "rate_limited":
            state.cooldown_until = time.time() + provider.cooldown_seconds
            state.reason = "rate_limited"
        elif error.cooldown_reason == "stream_unstable":
            state.cooldown_until = time.time() + max(5, min(10, provider.cooldown_seconds))
            state.reason = "stream_unstable"
        elif state.consecutive_failures >= provider.max_consecutive_failures:
            state.cooldown_until = time.time() + provider.cooldown_seconds
            state.reason = "cooldown"
        self._provider_circuits[provider_id] = state

    def _provider_cooldown_remaining(self, provider_id: str) -> int:
        state = self._provider_circuits.get(provider_id, ProviderCircuitState())
        return max(0, int(state.cooldown_until - time.time()))

    def _provider_misconfiguration(self, provider: ProviderRecord) -> str:
        settings = provider.settings
        if provider.kind == "mock":
            return ""
        if provider.kind == "ollama":
            if not settings.ollama_model:
                return "Ollama provider requires ollama_model"
            return ""
        if provider.kind == "openai_compatible":
            if not settings.openai_base_url:
                return "OpenAI-compatible provider requires openai_base_url"
            if not settings.openai_model:
                return "OpenAI-compatible provider requires openai_model"
            return ""
        if provider.kind == "http_backend":
            if not settings.api_url:
                return "HTTP backend provider requires api_url"
            return ""
        return ""

    def _cooldown_error(
        self,
        circuit: ProviderCircuitState,
        cooldown_remaining: int,
    ) -> GatewayErrorInfo:
        if circuit.reason == "rate_limited":
            return classify_gateway_error(
                f"Provider is rate limited and cooling down for {cooldown_remaining}s"
            )
        if circuit.reason == "stream_unstable":
            return classify_gateway_error(
                f"Provider stream was interrupted and is cooling down for {cooldown_remaining}s"
            )
        return classify_gateway_error(
            f"Provider is cooling down for {cooldown_remaining}s"
        )

    def _estimate_cost_usd(self, provider: ProviderRecord, metrics: ResponseMetrics) -> float:
        prompt_cost = (
            (metrics.prompt_tokens / 1000.0) * provider.prompt_cost_per_1k
            if provider.prompt_cost_per_1k > 0
            else 0.0
        )
        completion_cost = (
            (metrics.completion_tokens / 1000.0) * provider.completion_cost_per_1k
            if provider.completion_cost_per_1k > 0
            else 0.0
        )
        return round(prompt_cost + completion_cost, 6)

    def _summarize_groups(
        self,
        records,
        field_name: str,
    ) -> list[GatewayRequestSummaryGroup]:
        grouped: dict[str, list] = {}
        for record in records:
            key = getattr(record, field_name)
            if not key:
                key = "none" if field_name == "error_type" else "unknown"
            grouped.setdefault(key, []).append(record)
        rows: list[GatewayRequestSummaryGroup] = []
        for key in sorted(grouped):
            items = grouped[key]
            rows.append(
                GatewayRequestSummaryGroup(
                    key=key,
                    request_count=len(items),
                    completed_count=sum(1 for item in items if item.status == "completed"),
                    error_count=sum(1 for item in items if item.status == "error"),
                    avg_latency_ms=self._average_int(
                        item.latency_ms for item in items if item.latency_ms > 0
                    ),
                    avg_first_token_latency_ms=self._average_int(
                        item.first_token_latency_ms
                        for item in items
                        if item.first_token_latency_ms > 0
                    ),
                    total_tokens=sum(item.total_tokens for item in items),
                    estimated_cost_usd=round(
                        sum(item.estimated_cost_usd for item in items),
                        6,
                    ),
                )
            )
        return rows

    def _average_int(self, values) -> int:
        sequence = list(values)
        if not sequence:
            return 0
        return int(sum(sequence) / len(sequence))

    def _stream_terminal_error(
        self,
        *,
        request_id: str,
        client_request_id: str,
        provider_id: str,
        attempted_provider_ids: list[str],
        error: GatewayErrorInfo,
    ) -> Iterator[str]:
        yield self._sse(
            {
                "type": "error",
                "request_id": request_id,
                "client_request_id": client_request_id,
                "provider_id": provider_id,
                "attempted_provider_ids": attempted_provider_ids,
                "error_type": error.error_type,
                "status_code": error.http_status_code,
                "detail": error.detail,
                "status": "error",
            }
        )
        yield self._sse(
            {
                "type": "done",
                "request_id": request_id,
                "client_request_id": client_request_id,
                "provider_id": provider_id,
                "attempted_provider_ids": attempted_provider_ids,
                "error_type": error.error_type,
                "status": "error",
            }
        )

    def _sse(self, data: dict[str, object]) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
