from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darkfactory.models import Project, Session
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
        with patch.dict(
            os.environ,
            {
                "DARKFACTORY_OLLAMA_MODEL": "qwen2.5:latest",
            },
            clear=True,
        ):
            self.assertEqual(self.service.provider_name(), "ollama")

    def test_provider_name_supports_openai_compatible(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DARKFACTORY_OPENAI_BASE_URL": "http://localhost:8000/v1",
                "DARKFACTORY_OPENAI_MODEL": "gpt-like",
            },
            clear=True,
        ):
            self.assertEqual(self.service.provider_name(), "openai_compatible")

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


if __name__ == "__main__":
    unittest.main()
