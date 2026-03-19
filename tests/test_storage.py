from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darkfactory.storage import Storage


class StorageTests(unittest.TestCase):
    def test_storage_project_session_and_message_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            project_id = storage.create_project("测试项目", plant="测试电厂", unit="2#机")
            session_id = storage.create_session(project_id, "测试对话")
            storage.add_message(session_id, "user", "你好")
            storage.add_message(session_id, "assistant", "已收到")

            projects = storage.list_projects()
            sessions = storage.list_sessions(project_id)
            messages = storage.list_messages(session_id)

            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0].name, "测试项目")
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].name, "测试对话")
            self.assertEqual([message.role for message in messages], ["user", "assistant"])

    def test_app_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            self.assertIsNone(storage.get_state("last_session_id"))
            storage.set_state("last_session_id", "42")

            self.assertEqual(storage.get_state("last_session_id"), "42")


if __name__ == "__main__":
    unittest.main()
