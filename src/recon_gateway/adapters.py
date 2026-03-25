from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable, Iterator, Protocol

from recon.models import Message, Project, ProviderSettings, ResponseMetrics, Session
from recon.services import AssistantService

from .errors import GatewayProviderError, normalize_gateway_error


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


class BaseGatewayAdapter:
    def __init__(self, settings: ProviderSettings) -> None:
        self._settings = settings
        self._service = AssistantService(settings)
        self._last_result = GatewayAdapterResult(
            target=self.target_label(),
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

    def health_check(self) -> str:
        try:
            return self._service.health_check(self._settings)
        except Exception as exc:
            raise GatewayProviderError(normalize_gateway_error(exc)) from exc

    def target_label(self) -> str:
        return self._service.target_label(self._settings)

    def last_result(self) -> GatewayAdapterResult:
        return self._last_result

    def _capture_metrics(
        self,
        *,
        started_at: float,
        first_token_latency_ms: int,
    ) -> None:
        metrics = self._service.last_response_metrics()
        metrics.latency_ms = int((perf_counter() - started_at) * 1000)
        metrics.first_token_latency_ms = first_token_latency_ms
        self._last_result = GatewayAdapterResult(
            target=self.target_label(),
            metrics=metrics,
        )

    def _provider_error(self, exc: Exception) -> GatewayProviderError:
        return GatewayProviderError(normalize_gateway_error(exc))


class MockGatewayAdapter(BaseGatewayAdapter):
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
        self._service._last_metrics = ResponseMetrics(stream_mode="stream")
        try:
            for chunk in self._service._stream_via_mock(project=project, user_message=user_message):
                if chunk and first_token_latency_ms == 0:
                    first_token_latency_ms = int((perf_counter() - started_at) * 1000)
                yield chunk
        except Exception as exc:
            raise self._provider_error(exc) from exc
        self._capture_metrics(started_at=started_at, first_token_latency_ms=first_token_latency_ms)


class OllamaGatewayAdapter(BaseGatewayAdapter):
    def reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        client_request_id: str = "",
    ) -> str:
        started_at = perf_counter()
        timeout = float(self._service.request_timeout_seconds(self._settings))
        try:
            reply = self._service._reply_via_openai_compatible(
                base_url=self._settings.ollama_url or "http://127.0.0.1:11434/v1",
                api_key=self._settings.ollama_api_key or "ollama",
                model=self._settings.ollama_model,
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                timeout=timeout,
                client_request_id=client_request_id,
            )
        except Exception as exc:
            raise self._provider_error(exc) from exc
        self._capture_metrics(
            started_at=started_at,
            first_token_latency_ms=self._service.last_response_metrics().first_token_latency_ms,
        )
        return reply

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
        timeout = float(self._service.request_timeout_seconds(self._settings))
        self._service._last_metrics = ResponseMetrics(stream_mode="stream")
        try:
            for chunk in self._service._stream_via_openai_compatible(
                base_url=self._settings.ollama_url or "http://127.0.0.1:11434/v1",
                api_key=self._settings.ollama_api_key or "ollama",
                model=self._settings.ollama_model,
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                timeout=timeout,
                client_request_id=client_request_id,
            ):
                if chunk and first_token_latency_ms == 0:
                    first_token_latency_ms = int((perf_counter() - started_at) * 1000)
                yield chunk
        except Exception as exc:
            raise self._provider_error(exc) from exc
        self._capture_metrics(started_at=started_at, first_token_latency_ms=first_token_latency_ms)


class OpenAICompatibleGatewayAdapter(BaseGatewayAdapter):
    def reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        client_request_id: str = "",
    ) -> str:
        started_at = perf_counter()
        timeout = float(self._service.request_timeout_seconds(self._settings))
        try:
            reply = self._service._reply_via_openai_compatible(
                base_url=self._settings.openai_base_url,
                api_key=self._settings.openai_api_key,
                model=self._settings.openai_model,
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                timeout=timeout,
                client_request_id=client_request_id,
            )
        except Exception as exc:
            raise self._provider_error(exc) from exc
        self._capture_metrics(
            started_at=started_at,
            first_token_latency_ms=self._service.last_response_metrics().first_token_latency_ms,
        )
        return reply

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
        timeout = float(self._service.request_timeout_seconds(self._settings))
        self._service._last_metrics = ResponseMetrics(stream_mode="stream")
        try:
            for chunk in self._service._stream_via_openai_compatible(
                base_url=self._settings.openai_base_url,
                api_key=self._settings.openai_api_key,
                model=self._settings.openai_model,
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                timeout=timeout,
                client_request_id=client_request_id,
            ):
                if chunk and first_token_latency_ms == 0:
                    first_token_latency_ms = int((perf_counter() - started_at) * 1000)
                yield chunk
        except Exception as exc:
            raise self._provider_error(exc) from exc
        self._capture_metrics(started_at=started_at, first_token_latency_ms=first_token_latency_ms)


class HttpBackendGatewayAdapter(BaseGatewayAdapter):
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
        timeout = float(self._service.request_timeout_seconds(self._settings))
        self._service._last_metrics = ResponseMetrics(stream_mode="single")
        try:
            reply = self._service._reply_via_http(
                api_url=self._settings.api_url,
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                timeout=timeout,
                client_request_id=client_request_id,
            )
        except Exception as exc:
            raise self._provider_error(exc) from exc
        self._capture_metrics(
            started_at=started_at,
            first_token_latency_ms=int((perf_counter() - started_at) * 1000),
        )
        yield reply


class GatewayAdapterFactory:
    def create(self, settings: ProviderSettings) -> GatewayProviderAdapter:
        resolver = AssistantService(settings)
        provider = resolver.provider_name(settings)
        if provider == "ollama":
            return OllamaGatewayAdapter(settings)
        if provider == "openai_compatible":
            return OpenAICompatibleGatewayAdapter(settings)
        if provider == "http_backend":
            return HttpBackendGatewayAdapter(settings)
        return MockGatewayAdapter(settings)
