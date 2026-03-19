from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .models import Message, Project, Session
from .services import AssistantService
from .storage import Storage


ROLE_LABELS = {
    "user": "用户",
    "assistant": "系统",
}


@dataclass(slots=True)
class TreeRef:
    kind: str
    identifier: int


class AssistantWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        service: AssistantService,
        *,
        project: Project,
        session: Session,
        recent_messages: list[Message],
        user_message: str,
    ) -> None:
        super().__init__()
        self._service = service
        self._project = project
        self._session = session
        self._recent_messages = recent_messages
        self._user_message = user_message

    def run(self) -> None:
        try:
            reply = self._service.reply(
                project=self._project,
                session=self._session,
                recent_messages=self._recent_messages,
                user_message=self._user_message,
            )
        except Exception as exc:  # pragma: no cover - Qt thread path
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(reply)


class ProjectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, project: Project | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("项目设置" if project else "新建项目")
        self.resize(420, 220)

        self.name_input = QLineEdit(project.name if project else "")
        self.plant_input = QLineEdit(project.plant if project else "")
        self.unit_input = QLineEdit(project.unit if project else "")
        self.expert_type_input = QComboBox()
        self.expert_type_input.addItems(["热力专家", "汽机专家", "锅炉专家", "运行分析师"])
        if project:
            index = self.expert_type_input.findText(project.expert_type)
            if index >= 0:
                self.expert_type_input.setCurrentIndex(index)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("项目名称", self.name_input)
        form.addRow("电厂", self.plant_input)
        form.addRow("机组", self.unit_input)
        form.addRow("专家类型", self.expert_type_input)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict[str, str]:
        return {
            "name": self.name_input.text().strip(),
            "plant": self.plant_input.text().strip(),
            "unit": self.unit_input.text().strip(),
            "expert_type": self.expert_type_input.currentText().strip(),
        }


class MainWindow(QMainWindow):
    def __init__(self, storage: Storage, assistant: AssistantService) -> None:
        super().__init__()
        self.storage = storage
        self.assistant = assistant
        self.current_project: Project | None = None
        self.current_session: Session | None = None
        self.worker: AssistantWorker | None = None

        self.setWindowTitle("DarkFactory")
        self.resize(1180, 760)

        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderHidden(True)
        self.project_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.project_tree.itemSelectionChanged.connect(self.on_tree_selection_changed)
        self.project_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_tree.customContextMenuRequested.connect(self.open_tree_menu)

        self.project_info = QLabel("当前项目：-")
        self.session_info = QLabel("当前对话：-")
        self.project_meta = QLabel("项目上下文：-")
        self.project_meta.setWordWrap(True)

        self.message_list = QListWidget()
        self.message_list.setAlternatingRowColors(False)

        self.quick_buttons: list[QPushButton] = []
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("输入运行问题，或点击下方快捷按钮")
        self.input_line.returnPressed.connect(self.send_current_input)

        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self.send_current_input)

        self.new_project_button = QPushButton("新建项目")
        self.new_project_button.clicked.connect(self.create_project)

        self.new_session_button = QPushButton("新建对话")
        self.new_session_button.clicked.connect(self.create_session_for_current_project)

        self._build_ui()
        self._build_menu()
        self.refresh_tree()
        self.auto_select_initial_session()

    def _build_ui(self) -> None:
        container = QWidget()
        self.setCentralWidget(container)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.addWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("项目与对话")
        title.setStyleSheet("font-weight: 600;")

        button_row = QHBoxLayout()
        button_row.addWidget(self.new_project_button)
        button_row.addWidget(self.new_session_button)

        layout.addWidget(title)
        layout.addLayout(button_row)
        layout.addWidget(self.project_tree)
        return widget

    def _build_right_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.project_info)
        layout.addWidget(self.session_info)
        layout.addWidget(self.project_meta)
        layout.addWidget(self.message_list, stretch=1)

        quick_row = QHBoxLayout()
        for label in ("蒸汽不足", "负荷优化", "能效诊断"):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, value=label: self.send_quick_prompt(value))
            self.quick_buttons.append(button)
            quick_row.addWidget(button)
        layout.addLayout(quick_row)

        input_row = QHBoxLayout()
        input_row.addWidget(self.input_line, stretch=1)
        input_row.addWidget(self.send_button)
        layout.addLayout(input_row)

        return widget

    def _build_menu(self) -> None:
        create_project_action = QAction("新建项目", self)
        create_project_action.triggered.connect(self.create_project)

        create_session_action = QAction("新建对话", self)
        create_session_action.triggered.connect(self.create_session_for_current_project)

        edit_project_action = QAction("编辑项目", self)
        edit_project_action.triggered.connect(self.edit_current_project)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        file_menu.addAction(create_project_action)
        file_menu.addAction(create_session_action)
        file_menu.addAction(edit_project_action)

        self.statusBar().showMessage(
            f"模式：{self.assistant.mode_label()} | 数据库：{self.storage.db_path}"
        )

    def refresh_tree(self) -> None:
        previous_session_id = self.current_session.id if self.current_session else None
        self.project_tree.clear()

        for project in self.storage.list_projects():
            project_item = QTreeWidgetItem([project.name])
            project_item.setData(0, Qt.ItemDataRole.UserRole, TreeRef("project", project.id))
            self.project_tree.addTopLevelItem(project_item)
            project_item.setExpanded(True)

            for session in self.storage.list_sessions(project.id):
                session_item = QTreeWidgetItem([session.name])
                session_item.setData(0, Qt.ItemDataRole.UserRole, TreeRef("session", session.id))
                project_item.addChild(session_item)
                if previous_session_id == session.id:
                    self.project_tree.setCurrentItem(session_item)

        self.project_tree.expandAll()

    def auto_select_initial_session(self) -> None:
        if self.current_session is not None:
            return

        last_session_id = self.storage.get_state("last_session_id")
        if last_session_id and last_session_id.isdigit():
            session = self.storage.get_session(int(last_session_id))
            if session is not None:
                self.load_session(session.id)
                return

        for project in self.storage.list_projects():
            sessions = self.storage.list_sessions(project.id)
            if sessions:
                self.load_session(sessions[0].id)
                break

    def on_tree_selection_changed(self) -> None:
        selected = self.project_tree.selectedItems()
        if not selected:
            return

        ref = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(ref, TreeRef):
            return
        if ref.kind == "session":
            self.load_session(ref.identifier)
        elif ref.kind == "project":
            project = self.storage.get_project(ref.identifier)
            if project:
                self.current_project = project
                self.project_info.setText(f"当前项目：{project.name}")
                self.session_info.setText("当前对话：-")
                self.project_meta.setText(self.format_project_meta(project))

    def load_session(self, session_id: int) -> None:
        session = self.storage.get_session(session_id)
        if session is None:
            return
        project = self.storage.get_project(session.project_id)
        if project is None:
            return

        self.current_project = project
        self.current_session = session
        self.storage.set_state("last_session_id", str(session.id))
        self.project_info.setText(f"当前项目：{project.name}")
        self.session_info.setText(f"当前对话：{session.name}")
        self.project_meta.setText(self.format_project_meta(project))

        self.message_list.clear()
        for message in self.storage.list_messages(session.id):
            self.append_message(message.role, message.content)

    def format_project_meta(self, project: Project) -> str:
        parts = [
            f"电厂：{project.plant or '未设置'}",
            f"机组：{project.unit or '未设置'}",
            f"专家：{project.expert_type or '未设置'}",
        ]
        return "项目上下文：" + " | ".join(parts)

    def append_message(self, role: str, content: str) -> None:
        prefix = ROLE_LABELS.get(role, role)
        item = QListWidgetItem(f"{prefix}：\n{content}")
        if role == "user":
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.message_list.addItem(item)
        self.message_list.scrollToBottom()

    def create_project(self) -> None:
        dialog = ProjectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not values["name"]:
            QMessageBox.information(self, "提示", "项目名称不能为空。")
            return

        project_id = self.storage.create_project(
            name=values["name"],
            plant=values["plant"],
            unit=values["unit"],
            expert_type=values["expert_type"] or "热力专家",
        )
        session_id = self.storage.create_session(project_id, "默认对话")
        self.refresh_tree()
        self.load_session(session_id)

    def create_session_for_current_project(self) -> None:
        self.create_session()

    def create_session(self, project_id: int | None = None) -> None:
        effective_project_id = project_id
        if effective_project_id is None:
            if self.current_project is None:
                QMessageBox.information(self, "提示", "请先选择项目。")
                return
            effective_project_id = self.current_project.id

        project = self.storage.get_project(effective_project_id)
        if project is None:
            QMessageBox.information(self, "提示", "请先选择项目。")
            return
        name, accepted = QInputDialog.getText(self, "新建对话", "对话名称：", text="新对话")
        if not accepted or not name.strip():
            return
        session_id = self.storage.create_session(project.id, name.strip())
        self.refresh_tree()
        self.load_session(session_id)

    def open_tree_menu(self, position) -> None:  # type: ignore[no-untyped-def]
        item = self.project_tree.itemAt(position)
        menu = QMenu(self)

        new_project_action = menu.addAction("新建项目")
        new_project_action.triggered.connect(self.create_project)

        if item is None:
            menu.exec(self.project_tree.viewport().mapToGlobal(position))
            return

        ref = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(ref, TreeRef):
            return

        if ref.kind == "project":
            new_session_action = menu.addAction("新建对话")
            new_session_action.triggered.connect(lambda: self.create_session(ref.identifier))

            edit_action = menu.addAction("编辑项目")
            edit_action.triggered.connect(lambda: self.edit_project(ref.identifier))

            rename_action = menu.addAction("重命名项目")
            rename_action.triggered.connect(lambda: self.rename_project(ref.identifier))

            delete_action = menu.addAction("删除项目")
            delete_action.triggered.connect(lambda: self.delete_project(ref.identifier))
        else:
            rename_action = menu.addAction("重命名对话")
            rename_action.triggered.connect(lambda: self.rename_session(ref.identifier))

            delete_action = menu.addAction("删除对话")
            delete_action.triggered.connect(lambda: self.delete_session(ref.identifier))

        menu.exec(self.project_tree.viewport().mapToGlobal(position))

    def rename_project(self, project_id: int) -> None:
        project = self.storage.get_project(project_id)
        if project is None:
            return
        name, accepted = QInputDialog.getText(self, "重命名项目", "项目名称：", text=project.name)
        if not accepted or not name.strip():
            return
        self.storage.rename_project(project_id, name.strip())
        self.refresh_tree()

    def edit_current_project(self) -> None:
        if self.current_project is None:
            QMessageBox.information(self, "提示", "请先选择项目。")
            return
        self.edit_project(self.current_project.id)

    def edit_project(self, project_id: int) -> None:
        project = self.storage.get_project(project_id)
        if project is None:
            return

        dialog = ProjectDialog(self, project=project)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not values["name"]:
            QMessageBox.information(self, "提示", "项目名称不能为空。")
            return

        self.storage.update_project(
            project_id,
            name=values["name"],
            plant=values["plant"],
            unit=values["unit"],
            expert_type=values["expert_type"] or "热力专家",
        )
        self.refresh_tree()
        if self.current_session is not None:
            self.load_session(self.current_session.id)
        elif self.current_project is not None and self.current_project.id == project_id:
            updated_project = self.storage.get_project(project_id)
            if updated_project is not None:
                self.current_project = updated_project
                self.project_info.setText(f"当前项目：{updated_project.name}")
                self.project_meta.setText(self.format_project_meta(updated_project))

    def delete_project(self, project_id: int) -> None:
        result = QMessageBox.question(self, "删除项目", "确认删除该项目及其所有对话吗？")
        if result != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_project(project_id)
        if self.current_project and self.current_project.id == project_id:
            self.current_project = None
            self.current_session = None
            self.message_list.clear()
            self.project_info.setText("当前项目：-")
            self.session_info.setText("当前对话：-")
            self.project_meta.setText("项目上下文：-")
        self.refresh_tree()
        self.auto_select_initial_session()

    def rename_session(self, session_id: int) -> None:
        session = self.storage.get_session(session_id)
        if session is None:
            return
        name, accepted = QInputDialog.getText(self, "重命名对话", "对话名称：", text=session.name)
        if not accepted or not name.strip():
            return
        self.storage.rename_session(session_id, name.strip())
        self.refresh_tree()
        self.load_session(session_id)

    def delete_session(self, session_id: int) -> None:
        result = QMessageBox.question(self, "删除对话", "确认删除该对话吗？")
        if result != QMessageBox.StandardButton.Yes:
            return
        deleting_current = self.current_session and self.current_session.id == session_id
        self.storage.delete_session(session_id)
        self.refresh_tree()
        if deleting_current:
            self.current_session = None
            self.message_list.clear()
            self.session_info.setText("当前对话：-")
            self.auto_select_initial_session()

    def send_quick_prompt(self, label: str) -> None:
        quick_prompts = {
            "蒸汽不足": "请结合当前项目背景，分析蒸汽不足的可能原因并给出调整建议。",
            "负荷优化": "请从机组负荷分配角度给出优化建议，并说明约束与风险。",
            "能效诊断": "请按结论、原因分析、优化建议、影响评估输出当前能效诊断。",
        }
        self.input_line.setText(quick_prompts[label])
        self.send_current_input()

    def send_current_input(self) -> None:
        if self.current_project is None or self.current_session is None:
            QMessageBox.information(self, "提示", "请先创建并选择一个对话。")
            return

        message = self.input_line.text().strip()
        if not message:
            return

        self.storage.add_message(self.current_session.id, "user", message)
        self.append_message("user", message)
        self.input_line.clear()
        self.set_busy(True)

        recent_messages = self.storage.list_messages(self.current_session.id)[-12:]
        self.worker = AssistantWorker(
            self.assistant,
            project=self.current_project,
            session=self.current_session,
            recent_messages=recent_messages,
            user_message=message,
        )
        self.worker.succeeded.connect(self.on_assistant_reply)
        self.worker.failed.connect(self.on_assistant_error)
        self.worker.finished.connect(lambda: self.set_busy(False))
        self.worker.start()

    def on_assistant_reply(self, content: str) -> None:
        if self.current_session is None:
            return
        self.storage.add_message(self.current_session.id, "assistant", content)
        self.append_message("assistant", content)
        self.refresh_tree()
        self.load_session(self.current_session.id)

    def on_assistant_error(self, message: str) -> None:
        if self.current_session is None:
            return
        error_text = f"【错误】\n{message}"
        self.storage.add_message(self.current_session.id, "assistant", error_text)
        self.append_message("assistant", error_text)
        QMessageBox.warning(self, "请求失败", message)

    def set_busy(self, busy: bool) -> None:
        self.send_button.setEnabled(not busy)
        self.input_line.setEnabled(not busy)
        self.new_project_button.setEnabled(not busy)
        self.new_session_button.setEnabled(not busy)
        for button in self.quick_buttons:
            button.setEnabled(not busy)


def build_main_window() -> MainWindow:
    storage = Storage()
    storage.bootstrap()
    assistant = AssistantService()
    return MainWindow(storage=storage, assistant=assistant)


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or [])
    app.setApplicationName("DarkFactory")
    return app
