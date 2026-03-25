from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from recon.models import Project, ProviderSettings, Session
from recon.services import AssistantService, AssistantServiceError


class AssistantServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AssistantService()
        self.project = Project(
            id=1,
            name="示例项目",
            plant="示例电厂",
            unit="1#机",
            expert_type="热力专家",
            created_at="2026-03-19 00:00:00",
        )
        self.session = Session(
            id=1,
            project_id=1,
            name="蒸汽不足分析",
            summary="",
            updated_at="2026-03-19 00:00:00",
        )

    def test_mock_assistant_returns_structured_reply(self) -> None:
        reply = self.service._reply_via_mock(project=self.project, user_message="请分析蒸汽不足")

        self.assertIn("【结论】", reply)
        self.assertIn("【原因分析】", reply)
        self.assertIn("【优化建议】", reply)
        self.assertIn("【影响评估】", reply)

    def test_provider_name_defaults_to_mock(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.service.provider_name(), "mock")

    def test_provider_name_prefers_ollama_when_model_is_present(self) -> None:
        settings = ProviderSettings(provider="", ollama_model="qwen2.5:latest")
        self.assertEqual(self.service.provider_name(settings), "ollama")

    def test_provider_name_supports_openai_compatible(self) -> None:
        settings = ProviderSettings(
            provider="",
            openai_base_url="http://localhost:8000/v1",
            openai_model="gpt-like",
        )
        self.assertEqual(self.service.provider_name(settings), "openai_compatible")

    def test_provider_name_supports_openai_compatible_fallback_keys(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPENAI_BASE_URL": "http://localhost:8000/v1",
                "OPENAI_MODEL": "gpt-like",
            },
            clear=True,
        ):
            self.assertEqual(self.service.provider_name(), "openai_compatible")

    def test_target_label_uses_model_when_available(self) -> None:
        settings = ProviderSettings(provider="openai_compatible", openai_model="demo-model")
        self.assertEqual(self.service.target_label(settings), "demo-model")

    def test_extract_openai_stream_text_supports_string_delta(self) -> None:
        text = self.service._extract_openai_stream_text(
            {"choices": [{"delta": {"content": "hello"}}]}
        )
        self.assertEqual(text, "hello")

    def test_stream_reply_for_mock_yields_incremental_segments(self) -> None:
        chunks = list(
            self.service.stream_reply(
                project=self.project,
                session=self.session,
                recent_messages=[],
                user_message="请分析蒸汽不足",
                settings=ProviderSettings(provider="mock"),
            )
        )

        self.assertGreater(len(chunks), 1)
        self.assertIn("【结论】", "".join(chunks))
        self.assertEqual(self.service.last_response_metrics().stream_mode, "stream")

    def test_apply_usage_metrics_updates_last_response_metrics(self) -> None:
        self.service._apply_usage_metrics(
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )
        metrics = self.service.last_response_metrics()
        self.assertEqual(metrics.prompt_tokens, 10)
        self.assertEqual(metrics.completion_tokens, 20)
        self.assertEqual(metrics.total_tokens, 30)

    def test_build_provider_messages_keeps_project_context(self) -> None:
        messages = self.service._build_provider_messages(
            project=self.project,
            session=self.session,
            recent_messages=[],
            user_message="当前蒸汽不足怎么办？",
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("电力能源运行分析助手", messages[0]["content"])
        self.assertEqual(messages[1]["role"], "system")
        self.assertIn("示例电厂", messages[1]["content"])
        self.assertEqual(messages[-1]["role"], "user")
        self.assertIn("蒸汽不足", messages[-1]["content"])

    def test_health_check_for_mock_is_local(self) -> None:
        settings = ProviderSettings(provider="mock")
        self.assertIn("Mock provider", self.service.health_check(settings))

    def test_health_check_uses_models_endpoint_for_openai_compatible(self) -> None:
        settings = ProviderSettings(
            provider="openai_compatible",
            openai_base_url="http://localhost:8000/v1",
            openai_api_key="secret",
            openai_model="demo-model",
        )
        response = Mock()
        response.json.return_value = {"data": [{"id": "demo"}]}
        response.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = response
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=client)
        context_manager.__exit__ = Mock(return_value=None)

        with patch("httpx.Client", return_value=context_manager):
            message = self.service.health_check(settings)

        client.get.assert_called_once()
        self.assertIn("/models", client.get.call_args.kwargs["url"] if "url" in client.get.call_args.kwargs else client.get.call_args.args[0])
        self.assertIn("Connected successfully", message)

    def test_gateway_capabilities_derive_http_backend_urls(self) -> None:
        settings = ProviderSettings(
            provider="http_backend",
            api_url="http://localhost:8000/api/chat",
        )

        capabilities = self.service.gateway_capabilities(settings)

        self.assertEqual(capabilities["stream_url"], "http://localhost:8000/api/chat/stream")
        self.assertEqual(capabilities["health_url"], "http://localhost:8000/api/health")
        self.assertEqual(capabilities["providers_url"], "http://localhost:8000/api/providers")
        self.assertIn("{request_id}", capabilities["cancel_url_template"])

    def test_cancel_request_posts_to_derived_gateway_cancel_url(self) -> None:
        settings = ProviderSettings(
            provider="http_backend",
            api_url="http://localhost:8000/api/chat",
        )
        response = Mock()
        response.raise_for_status.return_value = None
        client = Mock()
        client.post.return_value = response
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=client)
        context_manager.__exit__ = Mock(return_value=None)

        with patch("httpx.Client", return_value=context_manager):
            cancel_url = self.service.cancel_request("req_123", settings)

        self.assertEqual(cancel_url, "http://localhost:8000/api/chat/req_123/cancel")
        client.post.assert_called_once()

    def test_reply_via_http_propagates_client_request_id_header(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"reply": "ok"}
        client = Mock()
        client.post.return_value = response
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=client)
        context_manager.__exit__ = Mock(return_value=None)

        with patch("httpx.Client", return_value=context_manager):
            reply = self.service._reply_via_http(
                api_url="http://localhost:8000/api/chat",
                project=self.project,
                session=self.session,
                recent_messages=[],
                user_message="hello",
                timeout=10.0,
                client_request_id="req-abc",
            )

        self.assertEqual(reply, "ok")
        self.assertEqual(
            client.post.call_args.kwargs["headers"]["X-Client-Request-Id"],
            "req-abc",
        )

    def test_reply_via_http_uses_backend_detail_when_status_fails(self) -> None:
        request = httpx.Request("POST", "http://localhost:8000/api/chat")
        response = httpx.Response(
            502,
            request=request,
            json={"detail": "upstream provider returned 404", "error_type": "upstream_http_error"},
        )
        client = Mock()
        client.post.return_value = response
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=client)
        context_manager.__exit__ = Mock(return_value=None)

        with patch("httpx.Client", return_value=context_manager):
            with self.assertRaises(AssistantServiceError) as error:
                self.service._reply_via_http(
                    api_url="http://localhost:8000/api/chat",
                    project=self.project,
                    session=self.session,
                    recent_messages=[],
                    user_message="hello",
                    timeout=10.0,
                    client_request_id="req-abc",
                )

        self.assertIn("upstream provider returned 404", str(error.exception))
        self.assertEqual(error.exception.error_type, "upstream_http_error")
        self.assertEqual(self.service.last_error_type(), "upstream_http_error")

    def test_stream_via_http_backend_yields_gateway_deltas(self) -> None:
        class StreamResponse:
            def raise_for_status(self) -> None:
                return None

            def iter_lines(self):
                yield 'data: {"type":"request","request_id":"req-1"}'
                yield 'data: {"type":"delta","delta":"hello "}'
                yield 'data: {"type":"delta","delta":"world"}'
                yield (
                    'data: {"type":"usage","prompt_tokens":3,'
                    '"completion_tokens":2,"total_tokens":5}'
                )
                yield 'data: {"type":"done","status":"completed"}'

        class ResponseContext:
            def __init__(self, response) -> None:
                self._response = response

            def __enter__(self):
                return self._response

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def stream(self, *args, **kwargs):
                return ResponseContext(StreamResponse())

        with patch("httpx.Client", return_value=FakeClient()):
            chunks = list(
                self.service._stream_via_http_backend(
                    api_url="http://localhost:8000/api/chat",
                    stream_url="http://localhost:8000/api/chat/stream",
                    project=self.project,
                    session=self.session,
                    recent_messages=[],
                    user_message="hello",
                    timeout=10.0,
                    client_request_id="req-abc",
                )
            )

        self.assertEqual(chunks, ["hello ", "world"])
        self.assertEqual(self.service.last_response_metrics().stream_mode, "stream")
        self.assertEqual(self.service.last_response_metrics().total_tokens, 5)

    def test_stream_via_http_backend_uses_sync_fallback_after_transport_timeout(self) -> None:
        class ResponseContext:
            def __enter__(self):
                raise httpx.ReadTimeout("timed out")

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        class FallbackResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"reply": "fallback reply"}

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def stream(self, *args, **kwargs):
                return ResponseContext()

            def post(self, *args, **kwargs):
                return FallbackResponse()

        with patch("httpx.Client", return_value=FakeClient()):
            chunks = list(
                self.service._stream_via_http_backend(
                    api_url="http://localhost:8000/api/chat",
                    stream_url="http://localhost:8000/api/chat/stream",
                    project=self.project,
                    session=self.session,
                    recent_messages=[],
                    user_message="hello",
                    timeout=10.0,
                    client_request_id="req-abc",
                )
            )

        self.assertEqual(chunks, ["fallback reply"])
        self.assertEqual(self.service.last_response_metrics().stream_mode, "single")

    def test_stream_via_http_backend_surfaces_gateway_error_event(self) -> None:
        class StreamResponse:
            def raise_for_status(self) -> None:
                return None

            def iter_lines(self):
                yield (
                    'data: {"type":"error","error_type":"upstream_timeout",'
                    '"status_code":504,"detail":"provider timed out"}'
                )
                yield 'data: {"type":"done","status":"error"}'

        class ResponseContext:
            def __init__(self, response) -> None:
                self._response = response

            def __enter__(self):
                return self._response

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def stream(self, *args, **kwargs):
                return ResponseContext(StreamResponse())

        with patch("httpx.Client", return_value=FakeClient()):
            with self.assertRaises(AssistantServiceError) as error:
                list(
                    self.service._stream_via_http_backend(
                        api_url="http://localhost:8000/api/chat",
                        stream_url="http://localhost:8000/api/chat/stream",
                        project=self.project,
                        session=self.session,
                        recent_messages=[],
                        user_message="hello",
                        timeout=10.0,
                        client_request_id="req-abc",
                    )
                )

        self.assertEqual(error.exception.error_type, "upstream_timeout")
        self.assertIn("provider timed out", str(error.exception))

    def test_fetch_gateway_providers_reads_gateway_registry(self) -> None:
        settings = ProviderSettings(
            provider="http_backend",
            api_url="http://localhost:8000/api/chat",
        )
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = [{"id": "mock"}]
        client = Mock()
        client.get.return_value = response
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=client)
        context_manager.__exit__ = Mock(return_value=None)

        with patch("httpx.Client", return_value=context_manager):
            providers = self.service.fetch_gateway_providers(settings)

        self.assertEqual(providers[0]["id"], "mock")
        self.assertIn("/api/providers", client.get.call_args.args[0])

    def test_reset_gateway_provider_posts_reset_endpoint(self) -> None:
        settings = ProviderSettings(
            provider="http_backend",
            api_url="http://localhost:8000/api/chat",
        )
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"provider_id": "mock", "status": "reset"}
        client = Mock()
        client.post.return_value = response
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=client)
        context_manager.__exit__ = Mock(return_value=None)

        with patch("httpx.Client", return_value=context_manager):
            result = self.service.reset_gateway_provider("mock", settings)

        self.assertEqual(result["status"], "reset")
        self.assertTrue(client.post.call_args.args[0].endswith("/api/providers/mock/reset"))

    def test_stream_via_openai_compatible_falls_back_to_single_after_early_disconnect(self) -> None:
        class BrokenStreamResponse:
            def raise_for_status(self) -> None:
                return None

            def iter_lines(self):
                raise httpx.RemoteProtocolError("peer closed connection without sending complete message body")
                yield ""

        class ResponseContext:
            def __init__(self, response) -> None:
                self._response = response

            def __enter__(self):
                return self._response

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        class FallbackResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "fallback reply",
                            }
                        }
                    ]
                }

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def stream(self, *args, **kwargs):
                return ResponseContext(BrokenStreamResponse())

            def post(self, *args, **kwargs):
                return FallbackResponse()

        with patch("httpx.Client", return_value=FakeClient()):
            chunks = list(
                self.service._stream_via_openai_compatible(
                    base_url="http://localhost:8000/v1",
                    api_key="secret",
                    model="demo-model",
                    project=self.project,
                    session=self.session,
                    recent_messages=[],
                    user_message="hello",
                    timeout=10.0,
                    client_request_id="req-123",
                )
            )

        self.assertEqual(chunks, ["fallback reply"])
        self.assertEqual(self.service.last_response_metrics().stream_mode, "single")

    def test_stream_via_openai_compatible_normalizes_partial_disconnect_error(self) -> None:
        class BrokenStreamResponse:
            def raise_for_status(self) -> None:
                return None

            def iter_lines(self):
                yield 'data: {"choices":[{"delta":{"content":"hello"}}]}'
                raise httpx.RemoteProtocolError("peer closed connection without sending complete message body")

        class ResponseContext:
            def __init__(self, response) -> None:
                self._response = response

            def __enter__(self):
                return self._response

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def stream(self, *args, **kwargs):
                return ResponseContext(BrokenStreamResponse())

        with patch("httpx.Client", return_value=FakeClient()):
            with self.assertRaises(AssistantServiceError) as error:
                list(
                    self.service._stream_via_openai_compatible(
                        base_url="http://localhost:8000/v1",
                        api_key="secret",
                        model="demo-model",
                        project=self.project,
                        session=self.session,
                        recent_messages=[],
                        user_message="hello",
                        timeout=10.0,
                        client_request_id="req-123",
                    )
                )

        self.assertIn("closed before the response completed", str(error.exception))
        self.assertEqual(error.exception.error_type, "stream_interrupted")
        self.assertNotIn("incomplete chunked read", str(error.exception).lower())

    def test_reply_via_openai_compatible_retries_non_stream_after_partial_disconnect(self) -> None:
        class BrokenStreamResponse:
            def raise_for_status(self) -> None:
                return None

            def iter_lines(self):
                yield 'data: {"choices":[{"delta":{"content":"partial"}}]}'
                raise httpx.RemoteProtocolError("peer closed connection without sending complete message body")

        class ResponseContext:
            def __init__(self, response) -> None:
                self._response = response

            def __enter__(self):
                return self._response

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        class FallbackResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "final non-stream reply",
                            }
                        }
                    ]
                }

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def stream(self, *args, **kwargs):
                return ResponseContext(BrokenStreamResponse())

            def post(self, *args, **kwargs):
                return FallbackResponse()

        with patch("httpx.Client", return_value=FakeClient()):
            reply = self.service._reply_via_openai_compatible(
                base_url="http://localhost:8000/v1",
                api_key="secret",
                model="demo-model",
                project=self.project,
                session=self.session,
                recent_messages=[],
                user_message="hello",
                timeout=10.0,
                client_request_id="req-123",
            )

        self.assertEqual(reply, "final non-stream reply")
        self.assertEqual(self.service.last_response_metrics().stream_mode, "single")

    def test_non_stream_openai_rate_limit_raises_typed_error(self) -> None:
        request = httpx.Request("POST", "http://localhost:8000/v1/chat/completions")
        response = httpx.Response(429, request=request)

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def post(self, *args, **kwargs):
                return response

        with patch("httpx.Client", return_value=FakeClient()):
            with self.assertRaises(AssistantServiceError) as error:
                self.service._request_openai_compatible_non_stream(
                    base_url="http://localhost:8000/v1",
                    api_key="secret",
                    model="demo-model",
                    project=self.project,
                    session=self.session,
                    recent_messages=[],
                    user_message="hello",
                    timeout=10.0,
                    client_request_id="req-123",
                )

        self.assertEqual(error.exception.error_type, "rate_limited")
        self.assertEqual(error.exception.http_status_code, 429)

    def test_sync_retry_policy_retries_timeout_but_not_rate_limit(self) -> None:
        timeout_error = AssistantServiceError(
            error_type="upstream_timeout",
            detail="timeout",
            http_status_code=504,
            retryable=True,
        )
        rate_limit_error = AssistantServiceError(
            error_type="rate_limited",
            detail="429",
            http_status_code=429,
            retryable=False,
        )

        self.assertTrue(self.service._sync_retry_policy(timeout_error))
        self.assertFalse(self.service._sync_retry_policy(rate_limit_error))


if __name__ == "__main__":
    unittest.main()
