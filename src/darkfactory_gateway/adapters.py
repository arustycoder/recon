from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable, Iterator, Protocol

from darkfactory.models import Message, Project, ProviderSettings, ResponseMetrics, Session
from darkfactory.services import AssistantService


@dataclass(slots=True)
class GatewayAdapterResult:
    target: str
    metrics: ResponseMetrics


class GatewayProviderAdapter(Protocol):
    def reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        client_request_id: str = "",
    ) -> str: ...

    def stream_reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        client_request_id: str = "",
    ) -> Iterator[str]: ...

    def health_check(self) -> str: ...

    def target_label(self) -> str: ...

    def last_result(self) -> GatewayAdapterResult: ...


class AssistantServiceAdapter:
    def __init__(self, settings: ProviderSettings) -> None:
        self._settings = settings
        self._service = AssistantService(settings)
        self._last_result = GatewayAdapterResult(
            target=self._service.target_label(settings),
            metrics=ResponseMetrics(),
        )

    def reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        client_request_id: str = "",
    ) -> str:
        return "".join(
            self.stream_reply(
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                client_request_id=client_request_id,
            )
        )

    def stream_reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        client_request_id: str = "",
    ) -> Iterator[str]:
        started_at = perf_counter()
        first_token_latency_ms = 0
        for chunk in self._service.stream_reply(
            project=project,
            session=session,
            recent_messages=recent_messages,
            user_message=user_message,
            settings=self._settings,
            client_request_id=client_request_id,
        ):
            if chunk and first_token_latency_ms == 0:
                first_token_latency_ms = int((perf_counter() - started_at) * 1000)
            yield chunk

        metrics = self._service.last_response_metrics()
        metrics.latency_ms = int((perf_counter() - started_at) * 1000)
        metrics.first_token_latency_ms = first_token_latency_ms
        self._last_result = GatewayAdapterResult(
            target=self._service.target_label(self._settings),
            metrics=metrics,
        )

    def health_check(self) -> str:
        return self._service.health_check(self._settings)

    def target_label(self) -> str:
        return self._service.target_label(self._settings)

    def last_result(self) -> GatewayAdapterResult:
        return self._last_result


class GatewayAdapterFactory:
    def create(self, settings: ProviderSettings) -> GatewayProviderAdapter:
        return AssistantServiceAdapter(settings)
