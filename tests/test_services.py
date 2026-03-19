from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darkfactory.models import Project, ProviderSettings, Session
from darkfactory.services import AssistantService


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


if __name__ == "__main__":
    unittest.main()
