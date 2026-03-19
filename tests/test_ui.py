from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtWidgets import QLabel

from darkfactory.services import AssistantService
from darkfactory.storage import Storage
from darkfactory.ui import MainWindow, create_application


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_application([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp_dir.name) / "darkfactory.db")
        self.storage.bootstrap()
        self.window = MainWindow(storage=self.storage, assistant=AssistantService())

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

        self.window.start_pending_response(session_id)

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

        self.window.refresh_tree()
        self.window.start_pending_response(origin_session_id)
        self.window.load_session(second_session_id)

        self.window.on_assistant_reply(origin_session_id, "后台回复")
        self.window.on_request_finished(origin_session_id)

        origin_messages = self.storage.list_messages(origin_session_id)
        self.assertEqual(origin_messages[-1].content, "后台回复")
        self.assertIsNotNone(self.window.current_session)
        self.assertEqual(self.window.current_session.id, second_session_id)
        self.assertIsNone(self.window.pending_session_id)

    def test_finishing_current_session_reply_does_not_touch_deleted_placeholder(self) -> None:
        self.assertIsNotNone(self.window.current_session)
        session_id = self.window.current_session.id

        self.window.start_pending_response(session_id)
        self.window.on_assistant_reply(session_id, "当前会话回复")
        self.window.on_request_finished(session_id)

        messages = self.storage.list_messages(session_id)
        self.assertEqual(messages[-1].content, "当前会话回复")
        self.assertIsNone(self.window.pending_message_item)


if __name__ == "__main__":
    unittest.main()
