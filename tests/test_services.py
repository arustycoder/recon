from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darkfactory.models import Project
from darkfactory.services import AssistantService


class AssistantServiceTests(unittest.TestCase):
    def test_mock_assistant_returns_structured_reply(self) -> None:
        service = AssistantService()
        project = Project(
            id=1,
            name="示例项目",
            plant="示例电厂",
            unit="1#机",
            expert_type="热力专家",
            created_at="2026-03-19 00:00:00",
        )

        reply = service._reply_via_mock(project=project, user_message="请分析蒸汽不足")

        self.assertIn("【结论】", reply)
        self.assertIn("【原因分析】", reply)
        self.assertIn("【优化建议】", reply)
        self.assertIn("【影响评估】", reply)


if __name__ == "__main__":
    unittest.main()
