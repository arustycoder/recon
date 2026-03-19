from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Iterator

from darkfactory.models import Message, Project, Session
from darkfactory.services import AssistantService

from .models import GatewayChatRequest, GatewayChatResponse
from .registry import ProviderRecord, ProviderRegistry
from .skills import SkillRegistry


@dataclass(slots=True)
class RequestState:
    request_id: str
    canceled: bool = False


class RequestTracker:
    def __init__(self) -> None:
        self._states: dict[str, RequestState] = {}

    def create(self) -> str:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        self._states[request_id] = RequestState(request_id=request_id)
        return request_id

    def cancel(self, request_id: str) -> bool:
        state = self._states.get(request_id)
        if state is None:
            return False
        state.canceled = True
        return True

    def is_canceled(self, request_id: str) -> bool:
        state = self._states.get(request_id)
        return state.canceled if state else False

    def complete(self, request_id: str) -> None:
        self._states.pop(request_id, None)


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
        return {"status": "ok"}

    def list_providers(self):
        return self.provider_registry.infos()

    def list_skills(self):
        return self.skill_registry.infos()

    def chat(self, request: GatewayChatRequest) -> GatewayChatResponse:
        provider = self.provider_registry.get(request.provider_id)
        assistant = AssistantService(provider.settings)
        project, session, recent_messages, user_message = self._to_domain_inputs(request)
        reply = "".join(
            assistant.stream_reply(
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                settings=provider.settings,
            )
        )
        metrics = assistant.last_response_metrics()
        return GatewayChatResponse(
            request_id=self.request_tracker.create(),
            provider_id=provider.id,
            reply=reply,
            stream_mode=metrics.stream_mode,
            prompt_tokens=metrics.prompt_tokens,
            completion_tokens=metrics.completion_tokens,
            total_tokens=metrics.total_tokens,
        )

    def stream_chat(self, request: GatewayChatRequest) -> Iterator[str]:
        request_id = self.request_tracker.create()
        provider = self.provider_registry.get(request.provider_id)
        assistant = AssistantService(provider.settings)
        project, session, recent_messages, user_message = self._to_domain_inputs(request)

        yield self._sse({"type": "request", "request_id": request_id, "provider_id": provider.id})
        try:
            for chunk in assistant.stream_reply(
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                settings=provider.settings,
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
            yield self._sse({"type": "done", "request_id": request_id})
        finally:
            self.request_tracker.complete(request_id)

    def cancel(self, request_id: str) -> str:
        if self.request_tracker.cancel(request_id):
            return "cancel_requested"
        return "unknown_request"

    def _to_domain_inputs(
        self,
        request: GatewayChatRequest,
    ) -> tuple[Project, Session, list[Message], str]:
        provider_prompt = self.skill_registry.prompt_for(request.skill_ids, request)
        user_message = request.message
        if provider_prompt:
            user_message = f"{request.message}\n\n[Gateway Skills]\n{provider_prompt}"

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

    def _sse(self, data: dict[str, object]) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
