from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtWidgets import QLabel

from darkfactory.models import ProviderSettings
from darkfactory.services import AssistantService
from darkfactory.storage import Storage
from darkfactory.ui import (
    MainWindow,
    RequestContext,
    RequestLogDialog,
    WorkerResult,
    create_application,
)


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_application([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp_dir.name) / "darkfactory.db")
        self.storage.bootstrap()
        self.window = MainWindow(
            storage=self.storage,
            assistant=AssistantService(ProviderSettings(provider="mock")),
        )

    def tearDown(self) -> None:
        self.window.close()
        self.temp_dir.cleanup()

    def message_body_text(self, row: int) -> str:
        item = self.window.message_list.item(row)
        widget = self.window.message_list.itemWidget(item)
        self.assertIsNotNone(widget)
        labels = widget.findChildren(QLabel)
        self.assertGreaterEqual(len(labels), 2)
        return labels[-1].text()

    def test_pending_message_and_slow_notice_are_visible(self) -> None:
        self.assertIsNotNone(self.window.current_session)
        session_id = self.window.current_session.id
        baseline_count = self.window.message_list.count()
        request_id = self.window.next_request_id()

        self.window.start_pending_response(request_id, session_id)

        self.assertEqual(self.window.message_list.count(), baseline_count + 1)
        self.assertIn("正在思考", self.message_body_text(self.window.message_list.count() - 1))

        self.window.on_slow_response_timeout()

        self.assertIn("请求耗时较长", self.message_body_text(self.window.message_list.count() - 1))
        self.assertIn("请求耗时较长", self.window.statusBar().currentMessage())

    def test_reply_is_written_to_origin_session_after_switch(self) -> None:
        self.assertIsNotNone(self.window.current_project)
        self.assertIsNotNone(self.window.current_session)
        origin_session_id = self.window.current_session.id
        second_session_id = self.storage.create_session(self.window.current_project.id, "第二对话")
        request_id = self.window.next_request_id()

        self.window.refresh_tree()
        self.window.start_pending_response(request_id, origin_session_id)
        self.window.load_session(second_session_id)

        self.window.on_assistant_reply(
            request_id,
            origin_session_id,
            WorkerResult(provider="mock", target="mock", latency_ms=10, content="后台回复"),
        )
        self.window.on_request_finished(request_id, origin_session_id)

        origin_messages = self.storage.list_messages(origin_session_id)
        self.assertEqual(origin_messages[-1].content, "后台回复")
        self.assertIsNotNone(self.window.current_session)
        self.assertEqual(self.window.current_session.id, second_session_id)
        self.assertIsNone(self.window.pending_session_id)

    def test_finishing_current_session_reply_does_not_touch_deleted_placeholder(self) -> None:
        self.assertIsNotNone(self.window.current_session)
        session_id = self.window.current_session.id
        request_id = self.window.next_request_id()

        self.window.start_pending_response(request_id, session_id)
        self.window.on_assistant_reply(
            request_id,
            session_id,
            WorkerResult(provider="mock", target="mock", latency_ms=10, content="当前会话回复"),
        )
        self.window.on_request_finished(request_id, session_id)

        messages = self.storage.list_messages(session_id)
        self.assertEqual(messages[-1].content, "当前会话回复")
        self.assertIsNone(self.window.pending_message_item)

    def test_auto_session_title_uses_first_prompt(self) -> None:
        self.assertIsNotNone(self.window.current_session)
        session_id = self.window.current_session.id

        self.window.apply_auto_session_title(
            session_id,
            "请结合当前项目背景，分析蒸汽不足的可能原因并给出调整建议。",
        )

        session = self.storage.get_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.name, "蒸汽不足分析")
        self.assertEqual(session.summary, "蒸汽不足分析")

    def test_stream_update_replaces_pending_message_body(self) -> None:
        self.assertIsNotNone(self.window.current_session)
        session_id = self.window.current_session.id
        request_id = self.window.next_request_id()

        self.window.start_pending_response(request_id, session_id)
        self.window.on_assistant_stream(request_id, session_id, "第一段回复")

        self.assertIn("第一段回复", self.message_body_text(self.window.message_list.count() - 1))
        self.assertIn("正在接收回复", self.window.statusBar().currentMessage())

    def test_cancel_active_request_writes_cancel_message_and_log(self) -> None:
        self.assertIsNotNone(self.window.current_session)
        session_id = self.window.current_session.id
        request_id = self.window.next_request_id()
        self.window.request_contexts[request_id] = RequestContext(
            session_id=session_id,
            provider="mock",
            target="mock",
            started_at=perf_counter(),
        )
        self.window.start_pending_response(request_id, session_id)
        self.window.set_busy(True)

        self.window.cancel_active_request()

        messages = self.storage.list_messages(session_id)
        logs = self.storage.list_request_logs()
        self.assertIn("已取消", messages[-1].content)
        self.assertEqual(logs[0].status, "canceled")
        self.assertFalse(self.window.is_busy)

    def test_request_log_dialog_shows_latest_logs(self) -> None:
        self.assertIsNotNone(self.window.current_session)
        self.storage.add_request_log(
            session_id=self.window.current_session.id,
            provider="mock",
            model="mock",
            status="success",
            latency_ms=33,
            detail="",
        )

        dialog = RequestLogDialog(self.storage)
        self.assertEqual(dialog.log_tree.topLevelItemCount(), 1)
        self.assertEqual(dialog.log_tree.topLevelItem(0).text(2), "mock")
        dialog.close()


if __name__ == "__main__":
    unittest.main()
