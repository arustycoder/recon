from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QCloseEvent, QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
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
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .config import (
    derive_http_cancel_url,
    derive_http_health_url,
    derive_http_providers_url,
    derive_http_stream_url,
    provider_settings_from_env,
)
from .models import Message, Project, ProviderSettings, Session
from .services import AssistantService
from .storage import Storage


ROLE_LABELS = {
    "user": "用户",
    "assistant": "系统",
}

URL_PATTERN = re.compile(r"(?P<url>(?:https?|file)://[^\s<>()]+)")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
TABLE_DIVIDER_PATTERN = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")
TEXT_ATTACHMENT_SUFFIXES = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".log",
    ".ini",
    ".cfg",
    ".toml",
    ".xml",
    ".html",
    ".htm",
    ".py",
    ".sql",
}
MAX_ATTACHMENT_EXCERPT_CHARS = 4000
MAX_ATTACHMENT_SUMMARY_COUNT = 5

GENERIC_SESSION_NAMES = {"默认对话", "新对话", "默认会话", "新会话"}

SCENARIO_LIBRARY: dict[str, list[tuple[str, str]]] = {
    "供汽与热力": [
        ("蒸汽不足", "请结合当前项目背景，分析蒸汽不足的可能原因并给出调整建议。"),
        ("抽汽冲突", "请分析抽汽需求冲突对当前机组运行的影响，并给出协调建议。"),
        ("供热波动", "请分析当前供热波动的可能原因、运行约束与调整建议。"),
    ],
    "负荷与调度": [
        ("负荷优化", "请从机组负荷分配角度给出优化建议，并说明约束与风险。"),
        ("调峰策略", "请结合机组特性分析当前调峰策略，并给出优化建议。"),
        ("机组切换", "请分析当前机组切换或运行方式调整的风险与注意事项。"),
    ],
    "能效与设备": [
        ("能效诊断", "请按结论、原因分析、优化建议、影响评估输出当前能效诊断。"),
        ("锅炉分析", "请从锅炉侧分析当前运行工况的效率与风险。"),
        ("汽机分析", "请从汽机侧分析当前运行工况的效率与风险。"),
    ],
}


def format_local_timestamp(value: str) -> str:
    text = value.strip()
    if not text:
        return value
    for parser in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, parser).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    return value


def _linkify_plain_text(text: str) -> str:
    if not text:
        return ""
    parts: list[str] = []
    last = 0
    for match in URL_PATTERN.finditer(text):
        parts.append(html.escape(text[last : match.start()]))
        url = match.group("url")
        safe_url = html.escape(url, quote=True)
        parts.append(f'<a href="{safe_url}">{html.escape(url)}</a>')
        last = match.end()
    parts.append(html.escape(text[last:]))
    return "".join(parts)


def render_inline_rich_text(text: str) -> str:
    if not text:
        return ""
    parts: list[str] = []
    last = 0
    for match in MARKDOWN_LINK_PATTERN.finditer(text):
        parts.append(_linkify_plain_text(text[last : match.start()]))
        label = html.escape(match.group(1))
        url = html.escape(match.group(2), quote=True)
        parts.append(f'<a href="{url}">{label}</a>')
        last = match.end()
    parts.append(_linkify_plain_text(text[last:]))
    return "".join(parts)


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _is_markdown_table(lines: list[str], start: int) -> bool:
    if start + 1 >= len(lines):
        return False
    if "|" not in lines[start]:
        return False
    if not TABLE_DIVIDER_PATTERN.match(lines[start + 1]):
        return False
    header = _split_table_row(lines[start])
    divider = _split_table_row(lines[start + 1])
    return len(header) >= 2 and len(header) == len(divider)


def _render_markdown_table(lines: list[str], start: int) -> tuple[str, int]:
    header = _split_table_row(lines[start])
    index = start + 2
    rows: list[list[str]] = []
    while index < len(lines):
        line = lines[index]
        if not line.strip() or "|" not in line:
            break
        cells = _split_table_row(line)
        if len(cells) != len(header):
            break
        rows.append(cells)
        index += 1

    header_html = "".join(f"<th>{render_inline_rich_text(cell)}</th>" for cell in header)
    row_html = []
    for row in rows:
        row_html.append(
            "<tr>" + "".join(f"<td>{render_inline_rich_text(cell)}</td>" for cell in row) + "</tr>"
        )
    table_html = (
        '<table cellspacing="0" cellpadding="6" border="1" '
        'style="border-collapse:collapse; margin:6px 0;">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table>"
    )
    return table_html, index


def render_message_content_html(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    pieces: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        joined = "<br>".join(render_inline_rich_text(line) for line in paragraph)
        pieces.append(f"<p>{joined}</p>")
        paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        if _is_markdown_table(lines, index):
            flush_paragraph()
            table_html, index = _render_markdown_table(lines, index)
            pieces.append(table_html)
            continue
        if not line.strip():
            flush_paragraph()
            index += 1
            continue
        paragraph.append(line)
        index += 1

    flush_paragraph()
    if not pieces:
        return "<p></p>"
    return "".join(pieces)


def extract_urls(content: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in URL_PATTERN.finditer(content):
        url = match.group("url")
        if url in seen:
            continue
        urls.append(url)
        seen.add(url)
    for match in MARKDOWN_LINK_PATTERN.finditer(content):
        url = match.group(2)
        if url in seen:
            continue
        urls.append(url)
        seen.add(url)
    return urls


@dataclass(slots=True)
class TreeRef:
    kind: str
    identifier: int


@dataclass(slots=True)
class WorkerResult:
    provider: str
    target: str
    latency_ms: int
    first_token_latency_ms: int = 0
    stream_mode: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error_type: str = ""
    content: str = ""
    error: str = ""


@dataclass(slots=True)
class RequestContext:
    session_id: int
    provider: str
    target: str
    started_at: float
    first_token_latency_ms: int = 0


class AssistantWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(object)
    streamed = Signal(str)

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
        started_at = perf_counter()
        provider = self._service.provider_name()
        target = self._service.target_label()
        accumulated_parts: list[str] = []
        first_token_latency_ms = 0
        try:
            for chunk in self._service.stream_reply(
                project=self._project,
                session=self._session,
                recent_messages=self._recent_messages,
                user_message=self._user_message,
            ):
                if not chunk:
                    continue
                accumulated_parts.append(chunk)
                if first_token_latency_ms == 0:
                    first_token_latency_ms = int((perf_counter() - started_at) * 1000)
                self.streamed.emit("".join(accumulated_parts))
        except Exception as exc:  # pragma: no cover - Qt thread path
            metrics = self._service.last_response_metrics()
            self.failed.emit(
                WorkerResult(
                    provider=provider,
                    target=target,
                    latency_ms=int((perf_counter() - started_at) * 1000),
                    first_token_latency_ms=first_token_latency_ms,
                    stream_mode=metrics.stream_mode,
                    prompt_tokens=metrics.prompt_tokens,
                    completion_tokens=metrics.completion_tokens,
                    total_tokens=metrics.total_tokens,
                    error_type=self._service.last_error_type(),
                    error=str(exc),
                )
            )
            return
        metrics = self._service.last_response_metrics()
        self.succeeded.emit(
            WorkerResult(
                provider=provider,
                target=target,
                latency_ms=int((perf_counter() - started_at) * 1000),
                first_token_latency_ms=first_token_latency_ms,
                stream_mode=metrics.stream_mode,
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
                total_tokens=metrics.total_tokens,
                content="".join(accumulated_parts),
            )
        )


class HealthCheckWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, service: AssistantService, settings: ProviderSettings) -> None:
        super().__init__()
        self._service = service
        self._settings = settings

    def run(self) -> None:
        try:
            message = self._service.health_check(self._settings)
        except Exception as exc:  # pragma: no cover - Qt thread path
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(message)


class MessageCard(QWidget):
    def __init__(
        self,
        *,
        role: str,
        content: str,
        timestamp: str = "刚刚",
        state_label: str = "",
        attachments: tuple = (),
    ) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(6, 2, 6, 2)

        bubble = QFrame()
        bubble.setObjectName(f"message-card-{role}")
        bubble.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 10, 12, 10)
        bubble_layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title = QLabel(f"{ROLE_LABELS.get(role, role)}  {timestamp}")
        title.setObjectName("message-card-title")

        state = QLabel(state_label)
        state.setObjectName("message-card-state")
        state.setVisible(bool(state_label))

        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(state)

        bubble_layout.addLayout(title_row)
        for block in self._build_message_blocks(content):
            bubble_layout.addWidget(block)
        for attachment in attachments:
            bubble_layout.addWidget(self._build_attachment_card(attachment))
        for url in extract_urls(content):
            bubble_layout.addWidget(self._build_link_card(url))

        outer_layout.addWidget(bubble, stretch=1)

        self.setStyleSheet(
            """
            QLabel#message-card-title {
                color: #5f6b7a;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#message-card-state {
                color: #b45309;
                background: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 9px;
                font-size: 11px;
                font-weight: 700;
                padding: 1px 8px;
            }
            QLabel#message-card-body {
                color: #1f2933;
                font-size: 13px;
                line-height: 1.35;
            }
            QFrame#message-attachment-card, QFrame#message-link-card {
                background: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                margin-top: 4px;
            }
            QLabel#attachment-title, QLabel#link-title {
                font-size: 12px;
                font-weight: 700;
                color: #111827;
            }
            QLabel#attachment-meta, QLabel#link-meta {
                font-size: 11px;
                color: #5f6b7a;
            }
            QFrame#message-card-user {
                background: #dbeafe;
                border: 1px solid #93c5fd;
                border-radius: 10px;
            }
            QFrame#message-card-assistant {
                background: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

    def _build_message_blocks(self, content: str) -> list[QWidget]:
        blocks: list[QWidget] = []
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")
        paragraph: list[str] = []
        index = 0

        def flush_paragraph() -> None:
            if not paragraph:
                return
            body = QLabel()
            body.setTextFormat(Qt.TextFormat.RichText)
            body.setOpenExternalLinks(True)
            body.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextBrowserInteraction
                | Qt.TextInteractionFlag.TextSelectableByMouse
            )
            body.setText("<p>" + "<br>".join(render_inline_rich_text(line) for line in paragraph) + "</p>")
            body.setWordWrap(True)
            body.setObjectName("message-card-body")
            blocks.append(body)
            paragraph.clear()

        while index < len(lines):
            line = lines[index]
            if _is_markdown_table(lines, index):
                flush_paragraph()
                table_widget, index = self._build_table_widget(lines, index)
                blocks.append(table_widget)
                continue
            if not line.strip():
                flush_paragraph()
                index += 1
                continue
            paragraph.append(line)
            index += 1
        flush_paragraph()
        if not blocks:
            body = QLabel("<p></p>")
            body.setTextFormat(Qt.TextFormat.RichText)
            body.setObjectName("message-card-body")
            blocks.append(body)
        return blocks

    def _build_table_widget(self, lines: list[str], start: int) -> tuple[QWidget, int]:
        header = _split_table_row(lines[start])
        index = start + 2
        rows: list[list[str]] = []
        while index < len(lines):
            line = lines[index]
            if not line.strip() or "|" not in line:
                break
            cells = _split_table_row(line)
            if len(cells) != len(header):
                break
            rows.append(cells)
            index += 1

        table = QTreeWidget()
        table.setRootIsDecorated(False)
        table.setAlternatingRowColors(True)
        table.setHeaderLabels(header)
        table.setUniformRowHeights(True)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setMaximumHeight(160)
        for row in rows:
            table.addTopLevelItem(QTreeWidgetItem(row))
        for column in range(table.columnCount()):
            table.resizeColumnToContents(column)
        return table, index

    def _build_attachment_card(self, attachment) -> QWidget:
        card = QFrame()
        card.setObjectName("message-attachment-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        title = QLabel(attachment.name)
        title.setObjectName("attachment-title")
        meta = QLabel(
            f"{attachment.media_type or 'file'} | {attachment.size_bytes} bytes | {attachment.path}"
        )
        meta.setObjectName("attachment-meta")
        meta.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(meta)
        if attachment.excerpt.strip():
            excerpt = QLabel(html.escape(attachment.excerpt[:240]).replace("\n", "<br>"))
            excerpt.setTextFormat(Qt.TextFormat.RichText)
            excerpt.setWordWrap(True)
            excerpt.setObjectName("attachment-meta")
            layout.addWidget(excerpt)
        link = QLabel(
            f'<a href="{html.escape(Path(attachment.path).as_uri(), quote=True)}">打开文件</a>'
        )
        link.setTextFormat(Qt.TextFormat.RichText)
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        link.setObjectName("attachment-meta")
        layout.addWidget(link)
        return card

    def _build_link_card(self, url: str) -> QWidget:
        card = QFrame()
        card.setObjectName("message-link-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        if url.startswith("file://"):
            title_text = Path(url.removeprefix("file://")).name or url
        elif "://" in url:
            title_text = url.split("/")[2]
        else:
            title_text = url

        title = QLabel(title_text)
        title.setObjectName("link-title")
        link = QLabel(f'<a href="{html.escape(url, quote=True)}">{html.escape(url)}</a>')
        link.setTextFormat(Qt.TextFormat.RichText)
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        link.setObjectName("link-meta")
        layout.addWidget(title)
        layout.addWidget(link)
        return card


class ChatInput(QTextEdit):
    send_requested = Signal()
    files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptRichText(False)
        self.setPlaceholderText("输入运行问题，或从左侧场景库选择模板")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.document().documentLayout().documentSizeChanged.connect(self.adjust_height)
        self.adjust_height()

    def adjust_height(self, *_args) -> None:
        line_count = max(1, self.document().blockCount())
        line_height = self.fontMetrics().lineSpacing()
        document_height = line_count * line_height
        frame_height = self.frameWidth() * 2
        padding = 10
        target = document_height + frame_height + padding
        self.setFixedHeight(max(40, min(target, 140)))

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if (
                key in {Qt.Key.Key_Return, Qt.Key.Key_Enter}
                and not (modifiers & Qt.KeyboardModifier.ShiftModifier)
            ):
                self.send_requested.emit()
                return True
        return super().event(event)

    def dragEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        mime = event.mimeData()
        if mime is not None and mime.hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        mime = event.mimeData()
        if mime is not None and mime.hasUrls():
            paths = []
            for url in mime.urls():
                local = url.toLocalFile()
                if local:
                    paths.append(local)
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, text: str) -> None:
        self.setPlainText(text)
        self.adjust_height()

    def clear(self) -> None:
        super().clear()
        self.adjust_height()


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


class SettingsDialog(QDialog):
    def __init__(
        self,
        *,
        service: AssistantService,
        settings: ProviderSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._health_worker: HealthCheckWorker | None = None

        self.setWindowTitle("模型与连接设置")
        self.resize(520, 420)

        self.provider_input = QComboBox()
        self.provider_input.addItem("Mock", "mock")
        self.provider_input.addItem("Ollama", "ollama")
        self.provider_input.addItem("OpenAI-Compatible", "openai_compatible")
        self.provider_input.addItem("HTTP Backend", "http_backend")
        provider_index = self.provider_input.findData(settings.provider)
        self.provider_input.setCurrentIndex(provider_index if provider_index >= 0 else 0)
        self.provider_input.currentIndexChanged.connect(self.on_provider_changed)

        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(5, 300)
        self.timeout_input.setValue(settings.request_timeout_seconds)
        self.timeout_input.setSuffix(" 秒")

        self.provider_stack = QStackedWidget()

        self.ollama_url_input = QLineEdit(settings.ollama_url)
        self.ollama_model_input = QLineEdit(settings.ollama_model)
        self.ollama_api_key_input = QLineEdit(settings.ollama_api_key)
        self.ollama_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.openai_base_url_input = QLineEdit(settings.openai_base_url)
        self.openai_model_input = QLineEdit(settings.openai_model)
        self.openai_api_key_input = QLineEdit(settings.openai_api_key)
        self.openai_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.api_url_input = QLineEdit(settings.api_url)
        self.api_health_url_input = QLineEdit(settings.api_health_url)
        self.api_stream_url_input = QLineEdit(settings.api_stream_url)
        self.api_cancel_url_template_input = QLineEdit(settings.api_cancel_url_template)
        self.api_providers_url_input = QLineEdit(settings.api_providers_url)

        self.provider_stack.addWidget(self._build_mock_page())
        self.provider_stack.addWidget(self._build_ollama_page())
        self.provider_stack.addWidget(self._build_openai_page())
        self.provider_stack.addWidget(self._build_http_page())

        self.connection_status = QLabel("可先测试当前配置，再保存。")
        self.connection_status.setWordWrap(True)
        self.connection_status.setStyleSheet("color: #5f6b7a;")

        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        header_form = QFormLayout()
        header_form.addRow("Provider", self.provider_input)
        header_form.addRow("请求超时", self.timeout_input)

        button_row = QHBoxLayout()
        button_row.addWidget(self.test_button)
        button_row.addStretch(1)
        button_row.addWidget(buttons)

        layout = QVBoxLayout(self)
        layout.addLayout(header_form)
        layout.addWidget(self.provider_stack)
        layout.addWidget(self.connection_status)
        layout.addLayout(button_row)

        self.on_provider_changed()

    def _build_mock_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        hint = QLabel("Mock 模式不需要额外配置，适合本地演示与 UI 测试。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return widget

    def _build_ollama_page(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.addRow("Base URL", self.ollama_url_input)
        form.addRow("Model", self.ollama_model_input)
        form.addRow("API Key", self.ollama_api_key_input)
        return widget

    def _build_openai_page(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.addRow("Base URL", self.openai_base_url_input)
        form.addRow("Model", self.openai_model_input)
        form.addRow("API Key", self.openai_api_key_input)
        return widget

    def _build_http_page(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.addRow("Chat URL", self.api_url_input)
        form.addRow("Stream URL", self.api_stream_url_input)
        form.addRow("Health URL", self.api_health_url_input)
        form.addRow("Cancel URL Template", self.api_cancel_url_template_input)
        form.addRow("Providers URL", self.api_providers_url_input)
        return widget

    def on_provider_changed(self) -> None:
        provider = self.provider_input.currentData()
        index_map = {
            "mock": 0,
            "ollama": 1,
            "openai_compatible": 2,
            "http_backend": 3,
        }
        self.provider_stack.setCurrentIndex(index_map.get(provider, 0))
        self.connection_status.setText("可先测试当前配置，再保存。")
        self.connection_status.setStyleSheet("color: #5f6b7a;")

    def values(self) -> ProviderSettings:
        provider = str(self.provider_input.currentData() or "mock")
        return ProviderSettings(
            provider=provider,
            ollama_url=self.ollama_url_input.text().strip() or "http://127.0.0.1:11434/v1",
            ollama_model=self.ollama_model_input.text().strip(),
            ollama_api_key=self.ollama_api_key_input.text().strip() or "ollama",
            openai_base_url=self.openai_base_url_input.text().strip(),
            openai_api_key=self.openai_api_key_input.text().strip(),
            openai_model=self.openai_model_input.text().strip(),
            api_url=self.api_url_input.text().strip(),
            api_health_url=self.api_health_url_input.text().strip(),
            api_stream_url=self.api_stream_url_input.text().strip(),
            api_cancel_url_template=self.api_cancel_url_template_input.text().strip(),
            api_providers_url=self.api_providers_url_input.text().strip(),
            request_timeout_seconds=int(self.timeout_input.value()),
        )

    def test_connection(self) -> None:
        self.test_button.setEnabled(False)
        self.connection_status.setText("正在测试连接...")
        self.connection_status.setStyleSheet("color: #5f6b7a;")
        self._health_worker = HealthCheckWorker(self._service, self.values())
        self._health_worker.succeeded.connect(self.on_test_success)
        self._health_worker.failed.connect(self.on_test_failure)
        self._health_worker.finished.connect(lambda: self.test_button.setEnabled(True))
        self._health_worker.finished.connect(lambda: setattr(self, "_health_worker", None))
        self._health_worker.start()

    def on_test_success(self, message: str) -> None:
        self.connection_status.setText(message)
        self.connection_status.setStyleSheet("color: #1d6f42;")

    def on_test_failure(self, message: str) -> None:
        self.connection_status.setText(message)
        self.connection_status.setStyleSheet("color: #b42318;")


class RequestLogDialog(QDialog):
    def __init__(self, storage: Storage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._storage = storage
        self.setWindowTitle("请求日志")
        self.resize(1180, 520)

        self.provider_filter = QComboBox()
        self.provider_filter.addItem("全部 Provider", "")
        for provider in ("mock", "ollama", "openai_compatible", "http_backend"):
            self.provider_filter.addItem(provider, provider)
        self.provider_filter.currentIndexChanged.connect(self.populate)

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", "")
        for status in ("success", "error", "canceled"):
            self.status_filter.addItem(status, status)
        self.status_filter.currentIndexChanged.connect(self.populate)

        self.error_type_filter = QComboBox()
        self.error_type_filter.addItem("全部错误类型", "")
        for error_type in (
            "rate_limited",
            "stream_interrupted",
            "upstream_timeout",
            "upstream_unreachable",
            "upstream_http_error",
            "empty_response",
            "invalid_response",
            "misconfigured",
            "unknown",
            "canceled",
        ):
            self.error_type_filter.addItem(error_type, error_type)
        self.error_type_filter.currentIndexChanged.connect(self.populate)

        self.summary_label = QLabel("暂无日志。")

        self.log_tree = QTreeWidget()
        self.log_tree.setRootIsDecorated(False)
        self.log_tree.setAlternatingRowColors(True)
        self.log_tree.setHeaderLabels(
            [
                "时间",
                "会话",
                "Provider",
                "目标",
                "状态",
                "错误类型",
                "模式",
                "首字延迟",
                "总耗时",
                "Prompt",
                "Completion",
                "Total",
                "详情",
            ]
        )

        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.populate)

        clear_button = QPushButton("清空当前筛选")
        clear_button.clicked.connect(self.clear_logs)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Provider"))
        filter_row.addWidget(self.provider_filter)
        filter_row.addWidget(QLabel("状态"))
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(QLabel("错误类型"))
        filter_row.addWidget(self.error_type_filter)
        filter_row.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addWidget(refresh_button)
        button_row.addWidget(clear_button)
        button_row.addStretch(1)
        button_row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.log_tree)
        layout.addLayout(button_row)

        self.populate()

    def populate(self) -> None:
        self.log_tree.clear()
        logs = self._storage.list_request_logs(
            limit=200,
            provider=str(self.provider_filter.currentData() or ""),
            status=str(self.status_filter.currentData() or ""),
            error_type=str(self.error_type_filter.currentData() or ""),
        )
        if logs:
            avg_latency = int(sum(entry.latency_ms for entry in logs) / len(logs))
            avg_first = int(sum(entry.first_token_latency_ms for entry in logs) / len(logs))
            self.summary_label.setText(
                f"共 {len(logs)} 条 | 平均首字延迟 {avg_first} ms | 平均总耗时 {avg_latency} ms"
            )
        else:
            self.summary_label.setText("暂无符合当前筛选条件的日志。")
        for entry in logs:
            session_label = "-"
            if entry.session_id is not None:
                session = self._storage.get_session(entry.session_id)
                session_label = session.name if session is not None else str(entry.session_id)
            item = QTreeWidgetItem(
                [
                    format_local_timestamp(entry.created_at),
                    session_label,
                    entry.provider,
                    entry.model,
                    entry.status,
                    entry.error_type or "-",
                    entry.stream_mode or "-",
                    str(entry.first_token_latency_ms),
                    str(entry.latency_ms),
                    str(entry.prompt_tokens),
                    str(entry.completion_tokens),
                    str(entry.total_tokens),
                    entry.detail or "-",
                ]
            )
            self.log_tree.addTopLevelItem(item)
        for column in range(self.log_tree.columnCount() - 1):
            self.log_tree.resizeColumnToContents(column)

    def clear_logs(self) -> None:
        provider = str(self.provider_filter.currentData() or "")
        status = str(self.status_filter.currentData() or "")
        error_type = str(self.error_type_filter.currentData() or "")
        if provider or status or error_type:
            message = "确认清空当前筛选条件下的请求日志吗？"
        else:
            message = "确认清空全部请求日志吗？"
        result = QMessageBox.question(self, "清空日志", message)
        if result != QMessageBox.StandardButton.Yes:
            return
        self._storage.clear_request_logs(
            provider=provider,
            status=status,
            error_type=error_type,
        )
        self.populate()


class GatewayProviderDialog(QDialog):
    def __init__(
        self,
        service: AssistantService,
        settings: ProviderSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._settings = settings
        self.setWindowTitle("Gateway Provider 运维")
        self.resize(980, 480)

        self.summary_label = QLabel("正在加载 Gateway provider 信息...")
        self.provider_tree = QTreeWidget()
        self.provider_tree.setRootIsDecorated(False)
        self.provider_tree.setAlternatingRowColors(True)
        self.provider_tree.setHeaderLabels(
            [
                "Provider",
                "Kind",
                "状态",
                "失败次数",
                "冷却剩余(s)",
                "详情",
            ]
        )

        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.populate)

        reset_button = QPushButton("重置选中 Provider")
        reset_button.clicked.connect(self.reset_selected_provider)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)

        button_row = QHBoxLayout()
        button_row.addWidget(refresh_button)
        button_row.addWidget(reset_button)
        button_row.addStretch(1)
        button_row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.provider_tree)
        layout.addLayout(button_row)

        self.populate()

    def populate(self) -> None:
        self.provider_tree.clear()
        try:
            providers = self._service.fetch_gateway_providers(self._settings)
        except Exception as exc:
            self.summary_label.setText(str(exc))
            return

        statuses: list[str] = []
        for provider in providers:
            provider_id = str(provider.get("id") or "")
            try:
                health = self._service.fetch_gateway_provider_health(provider_id, self._settings)
            except Exception as exc:
                health = {
                    "status": "error",
                    "detail": str(exc),
                    "consecutive_failures": 0,
                    "cooldown_remaining_seconds": 0,
                }
            item = QTreeWidgetItem(
                [
                    provider_id,
                    str(provider.get("kind") or ""),
                    str(health.get("status") or ""),
                    str(health.get("consecutive_failures") or 0),
                    str(health.get("cooldown_remaining_seconds") or 0),
                    str(health.get("detail") or ""),
                ]
            )
            self.provider_tree.addTopLevelItem(item)
            statuses.append(str(health.get("status") or "unknown"))

        if providers:
            self.summary_label.setText(
                f"共 {len(providers)} 个 Provider | 状态: {', '.join(statuses)}"
            )
        else:
            self.summary_label.setText("当前 Gateway 未返回任何 Provider。")
        for column in range(self.provider_tree.columnCount() - 1):
            self.provider_tree.resizeColumnToContents(column)

    def reset_selected_provider(self) -> None:
        item = self.provider_tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Provider 运维", "请先选择一个 Provider。")
            return
        provider_id = item.text(0).strip()
        if not provider_id:
            return
        try:
            result = self._service.reset_gateway_provider(provider_id, self._settings)
        except Exception as exc:
            QMessageBox.warning(self, "Provider 运维", str(exc))
            return
        QMessageBox.information(
            self,
            "Provider 运维",
            f"{provider_id} 已重置：{result.get('status', 'ok')}",
        )
        self.populate()


class MainWindow(QMainWindow):
    def __init__(self, storage: Storage, assistant: AssistantService) -> None:
        super().__init__()
        self.storage = storage
        self.assistant = assistant
        self.current_project: Project | None = None
        self.current_session: Session | None = None
        self.worker: AssistantWorker | None = None
        self.workers: dict[int, AssistantWorker] = {}
        self.request_contexts: dict[int, RequestContext] = {}
        self.canceled_request_ids: set[int] = set()
        self.request_counter = 0
        self.is_busy = False
        self.active_request_id: int | None = None
        self.pending_request_id: int | None = None
        self.pending_session_id: int | None = None
        self.pending_message_item: QListWidgetItem | None = None
        self.pending_message_text = "正在思考，请稍候..."
        self.pending_message_content = self.pending_message_text
        self.closing_after_requests = False
        self.selected_attachments: list[Path] = []

        self.slow_response_timer = QTimer(self)
        self.slow_response_timer.setSingleShot(True)
        self.slow_response_timer.timeout.connect(self.on_slow_response_timeout)

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
        self.message_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.message_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.message_list.setSpacing(6)

        self.empty_state = self._build_empty_state()
        self.message_stack = QStackedWidget()
        self.message_stack.addWidget(self.empty_state)
        self.message_stack.addWidget(self.message_list)

        self.scene_tree = QTreeWidget()
        self.scene_tree.setHeaderHidden(True)
        self.scene_tree.setRootIsDecorated(True)
        self.scene_tree.itemActivated.connect(self.on_scene_item_activated)
        self.scene_tree.itemClicked.connect(self.on_scene_item_clicked)

        self.attach_button = QPushButton("+")
        self.attach_button.setFixedSize(32, 32)
        self.attach_button.setToolTip("选择文件")
        self.attach_button.clicked.connect(self.choose_attachments)

        self.attachment_chip_container = QWidget()
        self.attachment_chip_layout = QHBoxLayout(self.attachment_chip_container)
        self.attachment_chip_layout.setContentsMargins(0, 0, 0, 0)
        self.attachment_chip_layout.setSpacing(6)
        self.attachment_chip_container.hide()

        self.clear_attachments_button = QPushButton("清空附件")
        self.clear_attachments_button.clicked.connect(self.clear_selected_attachments)
        self.clear_attachments_button.hide()

        self.input_line = ChatInput()
        self.input_line.send_requested.connect(self.send_current_input)
        self.input_line.files_dropped.connect(self.add_attachment_paths)

        self.action_button = QPushButton()
        self.action_button.setFixedSize(40, 40)
        self.action_button.setIconSize(QSize(20, 20))
        self.action_button.clicked.connect(self.on_action_button_clicked)
        self.action_button.setStyleSheet(
            """
            QPushButton {
                background: #111827;
                color: white;
                border: none;
                border-radius: 20px;
            }
            QPushButton:disabled {
                background: #9ca3af;
            }
            QPushButton:hover:!disabled {
                background: #1f2937;
            }
            """
        )

        self.new_project_button = QPushButton("新建项目")
        self.new_project_button.clicked.connect(self.create_project)

        self.new_session_button = QPushButton("新建对话")
        self.new_session_button.clicked.connect(self.create_session_for_current_project)

        self._build_ui()
        self._build_menu()
        self.populate_scene_library()
        self.refresh_tree()
        self.auto_select_initial_session()
        self.update_interaction_state()

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
        layout.addWidget(self.project_tree, stretch=3)

        scene_title = QLabel("场景库")
        scene_title.setStyleSheet("font-weight: 600; margin-top: 8px;")
        scene_hint = QLabel("按专题组织常用分析入口，适合放较多快捷模板。")
        scene_hint.setWordWrap(True)
        scene_hint.setStyleSheet("color: #5f6b7a; font-size: 12px;")

        layout.addWidget(scene_title)
        layout.addWidget(scene_hint)
        layout.addWidget(self.scene_tree, stretch=2)
        return widget

    def _build_right_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.project_info)
        layout.addWidget(self.session_info)
        layout.addWidget(self.project_meta)
        layout.addWidget(self.message_stack, stretch=1)

        attachment_row = QHBoxLayout()
        attachment_row.addWidget(self.attachment_chip_container, stretch=1)
        attachment_row.addWidget(self.clear_attachments_button)
        layout.addLayout(attachment_row)

        input_row = QHBoxLayout()
        input_row.addWidget(self.attach_button)
        input_row.addWidget(self.input_line, stretch=1)
        input_row.addWidget(self.action_button)
        layout.addLayout(input_row)

        return widget

    def _build_empty_state(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)

        title = QLabel("还没有选中对话")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1f2933;")

        subtitle = QLabel(
            "请先从左侧选择一个 Project 下的对话，或新建项目后开始分析。"
        )
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 13px; color: #5f6b7a;")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        return widget

    def _build_menu(self) -> None:
        create_project_action = QAction("新建项目", self)
        create_project_action.triggered.connect(self.create_project)

        create_session_action = QAction("新建对话", self)
        create_session_action.triggered.connect(self.create_session_for_current_project)

        edit_project_action = QAction("编辑项目", self)
        edit_project_action.triggered.connect(self.edit_current_project)

        settings_action = QAction("模型设置", self)
        settings_action.triggered.connect(self.open_settings_dialog)

        logs_action = QAction("请求日志", self)
        logs_action.triggered.connect(self.open_request_log_dialog)

        gateway_providers_action = QAction("Gateway Providers", self)
        gateway_providers_action.triggered.connect(self.open_gateway_provider_dialog)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        file_menu.addAction(create_project_action)
        file_menu.addAction(create_session_action)
        file_menu.addAction(edit_project_action)

        tools_menu = menubar.addMenu("工具")
        tools_menu.addAction(settings_action)
        tools_menu.addAction(logs_action)
        tools_menu.addAction(gateway_providers_action)

        self._set_status_message()

    def refresh_tree(self) -> None:
        previous_session_id = self.current_session.id if self.current_session else None
        self.project_tree.clear()

        for project in self.storage.list_projects():
            project_item = QTreeWidgetItem([project.name])
            project_item.setData(0, Qt.ItemDataRole.UserRole, TreeRef("project", project.id))
            self.project_tree.addTopLevelItem(project_item)
            project_item.setExpanded(True)

            for session in self.storage.list_sessions(project.id):
                session_label = session.name
                session_item = QTreeWidgetItem([session_label])
                session_item.setData(0, Qt.ItemDataRole.UserRole, TreeRef("session", session.id))
                project_item.addChild(session_item)
                if previous_session_id == session.id:
                    self.project_tree.setCurrentItem(session_item)

        self.project_tree.expandAll()
        self.update_interaction_state()

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
                self.current_session = None
                self.project_info.setText(f"当前项目：{project.name}")
                self.session_info.setText("当前对话：-")
                self.project_meta.setText(self.format_project_meta(project))
                self.message_list.clear()
                self.update_message_stack()
                self.update_interaction_state()

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
            self.append_message(
                message.role,
                message.content,
                timestamp=format_local_timestamp(message.created_at),
                attachments=message.attachments,
            )
        if self.pending_session_id == session.id and self.pending_message_item is None:
            self.pending_message_item = self.append_message(
                "assistant",
                self.pending_message_content,
                timestamp="处理中",
            )
        self.update_message_stack()
        self.update_interaction_state()

    def format_project_meta(self, project: Project) -> str:
        parts = [
            f"电厂：{project.plant or '未设置'}",
            f"机组：{project.unit or '未设置'}",
            f"专家：{project.expert_type or '未设置'}",
        ]
        return "项目上下文：" + " | ".join(parts)

    def append_message(
        self,
        role: str,
        content: str,
        *,
        timestamp: str = "刚刚",
        state_label: str = "",
        attachments: tuple = (),
    ) -> QListWidgetItem:
        item = QListWidgetItem()
        widget = MessageCard(
            role=role,
            content=content,
            timestamp=timestamp,
            state_label=state_label,
            attachments=attachments,
        )
        item.setSizeHint(widget.sizeHint())
        self.message_list.addItem(item)
        self.message_list.setItemWidget(item, widget)
        self.message_list.scrollToBottom()
        self.update_message_stack()
        return item

    def update_message_item(
        self,
        item: QListWidgetItem,
        *,
        role: str,
        content: str,
        timestamp: str = "刚刚",
        state_label: str = "",
        attachments: tuple = (),
    ) -> None:
        widget = MessageCard(
            role=role,
            content=content,
            timestamp=timestamp,
            state_label=state_label,
            attachments=attachments,
        )
        item.setSizeHint(widget.sizeHint())
        self.message_list.setItemWidget(item, widget)
        self.message_list.scrollToBottom()
        self.update_message_stack()

    def remove_message_item(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        try:
            row = self.message_list.row(item)
        except RuntimeError:
            return
        if row >= 0:
            removed = self.message_list.takeItem(row)
            del removed
        self.update_message_stack()

    def _set_status_message(self, detail: str | None = None) -> None:
        base = f"模式：{self.assistant.mode_label()} | 数据库：{self.storage.db_path}"
        if detail:
            self.statusBar().showMessage(f"{detail} | {base}")
            return
        self.statusBar().showMessage(base)

    def update_message_stack(self) -> None:
        has_active_session = self.current_session is not None
        has_messages = self.message_list.count() > 0
        if has_active_session or has_messages:
            self.message_stack.setCurrentWidget(self.message_list)
        else:
            self.message_stack.setCurrentWidget(self.empty_state)

    def update_interaction_state(self) -> None:
        has_session = self.current_session is not None
        self.input_line.setEnabled(has_session and not self.is_busy)
        self.attach_button.setEnabled(has_session and not self.is_busy)
        self.action_button.setEnabled(has_session)
        self.new_project_button.setEnabled(not self.is_busy)
        self.new_session_button.setEnabled(self.current_project is not None and not self.is_busy)
        self.scene_tree.setEnabled(has_session and not self.is_busy)
        self.clear_attachments_button.setEnabled(has_session and not self.is_busy)
        self.update_action_button()

    def set_busy(self, busy: bool) -> None:
        self.is_busy = busy
        self.update_interaction_state()

    def on_action_button_clicked(self) -> None:
        if self.is_busy:
            self.cancel_active_request()
            return
        self.send_current_input()

    def update_action_button(self) -> None:
        if self.is_busy:
            self.action_button.setIcon(self.build_coin_stop_icon())
            self.action_button.setToolTip("停止等待")
            return
        self.action_button.setIcon(self.build_send_icon())
        self.action_button.setToolTip("发送")

    def build_send_icon(self) -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(10, 15, 10, 5)
        arrow = QPolygonF(
            [
                QPointF(5, 9),
                QPointF(10, 4),
                QPointF(15, 9),
            ]
        )
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawPolygon(arrow)
        painter.end()
        return QIcon(pixmap)

    def build_coin_stop_icon(self) -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#000000")))
        painter.drawEllipse(QRectF(2, 2, 16, 16))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRect(QRectF(6, 6, 8, 8))
        painter.end()
        return QIcon(pixmap)

    def next_request_id(self) -> int:
        self.request_counter += 1
        return self.request_counter

    def choose_attachments(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        if not paths:
            return
        self.add_attachment_paths(paths)

    def add_attachment_paths(self, paths: list[str]) -> None:
        existing = {path.resolve() for path in self.selected_attachments}
        for raw_path in paths:
            path = Path(raw_path)
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in existing or not resolved.exists():
                continue
            self.selected_attachments.append(resolved)
            existing.add(resolved)
        self.update_attachment_summary()

    def clear_selected_attachments(self) -> None:
        self.selected_attachments.clear()
        self.update_attachment_summary()

    def remove_selected_attachment(self, path: Path) -> None:
        try:
            target = path.resolve()
        except OSError:
            target = path
        self.selected_attachments = [item for item in self.selected_attachments if item != target]
        self.update_attachment_summary()

    def update_attachment_summary(self) -> None:
        while self.attachment_chip_layout.count():
            item = self.attachment_chip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not self.selected_attachments:
            self.attachment_chip_container.hide()
            self.clear_attachments_button.hide()
            return
        for path in self.selected_attachments[:MAX_ATTACHMENT_SUMMARY_COUNT]:
            chip = QPushButton(path.name)
            chip.setToolTip(str(path))
            chip.setStyleSheet(
                """
                QPushButton {
                    text-align: left;
                    padding: 4px 10px;
                    border-radius: 10px;
                    background: #eef2ff;
                    border: 1px solid #c7d2fe;
                }
                QPushButton:hover {
                    background: #e0e7ff;
                }
                """
            )
            chip.clicked.connect(lambda _checked=False, attachment_path=path: self.remove_selected_attachment(attachment_path))
            self.attachment_chip_layout.addWidget(chip)
        if len(self.selected_attachments) > MAX_ATTACHMENT_SUMMARY_COUNT:
            extra_label = QLabel(f"等 {len(self.selected_attachments)} 个文件")
            extra_label.setStyleSheet("color: #5f6b7a; font-size: 12px;")
            self.attachment_chip_layout.addWidget(extra_label)
        self.attachment_chip_layout.addStretch(1)
        self.attachment_chip_container.show()
        self.clear_attachments_button.show()

    def build_attachment_prompt(self, attachments: list[Path]) -> str:
        if not attachments:
            return ""
        blocks = ["【附件】"]
        for path in attachments:
            excerpt = self.read_attachment_excerpt(path)
            if excerpt:
                blocks.append(
                    "\n".join(
                        [
                            f"文件：{path.name}",
                            f"路径：{path}",
                            f"链接：{path.as_uri()}",
                            "类型：文本附件",
                            "内容摘录：",
                            excerpt,
                        ]
                    )
                )
            else:
                blocks.append(
                    "\n".join(
                        [
                            f"文件：{path.name}",
                            f"路径：{path}",
                            f"链接：{path.as_uri()}",
                            "类型：二进制或暂不解析的文件",
                            "说明：当前版本保留文件引用，但不会直接提取二进制内容。",
                        ]
                    )
                )
        return "\n\n".join(blocks)

    def read_attachment_excerpt(self, path: Path) -> str:
        if path.suffix.lower() not in TEXT_ATTACHMENT_SUFFIXES:
            return ""
        try:
            raw = path.read_bytes()
        except OSError:
            return ""
        if b"\x00" in raw[:1024]:
            return ""
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            return ""
        excerpt = text.strip()
        if not excerpt:
            return ""
        if len(excerpt) > MAX_ATTACHMENT_EXCERPT_CHARS:
            excerpt = excerpt[:MAX_ATTACHMENT_EXCERPT_CHARS].rstrip() + "\n[内容已截断]"
        return excerpt

    def compose_outgoing_message(self, message: str, attachments: list[Path]) -> str:
        parts: list[str] = []
        attachment_prompt = self.build_attachment_prompt(attachments)
        if attachment_prompt:
            parts.append(attachment_prompt)
        if message.strip():
            parts.append(message.strip())
        return "\n\n".join(parts).strip()

    def persist_attachments(self, attachments: list[Path]) -> list[int]:
        attachment_ids: list[int] = []
        for path in attachments:
            try:
                stat = path.stat()
                size_bytes = int(stat.st_size)
            except OSError:
                size_bytes = 0
            media_type = path.suffix.lower().lstrip(".")
            excerpt = self.read_attachment_excerpt(path)
            attachment_ids.append(
                self.storage.upsert_attachment(
                    path=str(path),
                    name=path.name,
                    media_type=media_type,
                    size_bytes=size_bytes,
                    excerpt=excerpt,
                )
            )
        return attachment_ids

    def start_pending_response(self, request_id: int, session_id: int) -> None:
        self.active_request_id = request_id
        self.pending_request_id = request_id
        self.pending_session_id = session_id
        self.pending_message_content = self.pending_message_text
        if self.current_session is not None and self.current_session.id == session_id:
            self.pending_message_item = self.append_message(
                "assistant",
                self.pending_message_content,
                timestamp="处理中",
                state_label="输入中",
            )
        else:
            self.pending_message_item = None
        self.slow_response_timer.start(8000)
        self._set_status_message("等待模型回复")

    def clear_pending_response(self, request_id: int, session_id: int) -> None:
        if self.pending_request_id != request_id:
            return
        self.slow_response_timer.stop()
        if self.current_session is not None and self.current_session.id == session_id:
            self.remove_message_item(self.pending_message_item)
        self.pending_message_item = None
        self.pending_request_id = None
        self.pending_session_id = None
        self.pending_message_content = self.pending_message_text
        if self.active_request_id == request_id:
            self.active_request_id = None
        self._set_status_message()

    def on_slow_response_timeout(self) -> None:
        if self.pending_message_item is None or self.pending_session_id is None:
            return
        if self.current_session is None or self.current_session.id != self.pending_session_id:
            return
        self.update_message_item(
            self.pending_message_item,
            role="assistant",
            content="请求耗时较长，仍在等待模型返回，请稍候...",
            timestamp="处理中",
            state_label="输入中",
        )
        self.pending_message_content = "请求耗时较长，仍在等待模型返回，请稍候..."
        self._set_status_message("请求耗时较长")

    def ensure_pending_message_visible(self, session_id: int) -> None:
        if self.current_session is None or self.current_session.id != session_id:
            return
        if self.pending_message_item is None:
            self.pending_message_item = self.append_message(
                "assistant",
                self.pending_message_content,
                timestamp="处理中",
                state_label="输入中",
            )

    def on_assistant_stream(self, request_id: int, session_id: int, content: str) -> None:
        if request_id in self.canceled_request_ids:
            return
        if self.pending_request_id != request_id:
            return
        context = self.request_contexts.get(request_id)
        if context is not None and context.first_token_latency_ms == 0:
            context.first_token_latency_ms = int((perf_counter() - context.started_at) * 1000)
        self.pending_message_content = content or self.pending_message_text
        self.ensure_pending_message_visible(session_id)
        if self.pending_message_item is not None:
            self.update_message_item(
                self.pending_message_item,
                role="assistant",
                content=self.pending_message_content,
                timestamp="生成中",
                state_label="输入中",
            )
        self._set_status_message("正在接收回复")

    def summarize_session_title(self, message: str) -> str:
        compact = " ".join(part for part in message.replace("\n", " ").split() if part).strip()
        if not compact:
            return "新对话"
        keyword_titles = [
            ("蒸汽", "蒸汽不足分析"),
            ("负荷", "负荷优化建议"),
            ("能效", "能效诊断"),
            ("锅炉", "锅炉运行分析"),
            ("汽机", "汽机运行分析"),
        ]
        for keyword, title in keyword_titles:
            if keyword in compact:
                return title

        trimmed = compact
        for prefix in ("请结合当前项目背景，", "请", "帮我", "帮忙", "分析", "一下", "一下子"):
            if trimmed.startswith(prefix):
                trimmed = trimmed.removeprefix(prefix).strip()
        trimmed = trimmed.rstrip("。！？!?，,；;：:")
        if not trimmed:
            trimmed = compact
        if len(trimmed) > 18:
            trimmed = trimmed[:18].rstrip()
        return trimmed or "新对话"

    def apply_auto_session_title(self, session_id: int, message: str) -> None:
        session = self.storage.get_session(session_id)
        if session is None:
            return
        title = self.summarize_session_title(message)
        new_name = title if session.name in GENERIC_SESSION_NAMES else None
        new_summary = title if not session.summary.strip() else None
        self.storage.update_session_metadata(session_id, name=new_name, summary=new_summary)

    def open_settings_dialog(self) -> None:
        dialog = SettingsDialog(
            service=self.assistant,
            settings=self.assistant.current_settings(),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        settings = dialog.values()
        self.storage.save_provider_settings(settings)
        self.assistant.update_settings(settings)
        self._set_status_message("设置已保存")

    def open_request_log_dialog(self) -> None:
        dialog = RequestLogDialog(self.storage, self)
        dialog.exec()

    def open_gateway_provider_dialog(self) -> None:
        dialog = GatewayProviderDialog(
            self.assistant,
            self.assistant.current_settings(),
            self,
        )
        dialog.exec()

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
        self.update_message_stack()
        self.update_interaction_state()

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
        self.update_message_stack()
        self.update_interaction_state()

    def populate_scene_library(self) -> None:
        self.scene_tree.clear()
        for category, scenes in SCENARIO_LIBRARY.items():
            category_item = QTreeWidgetItem([category])
            category_item.setFlags(
                category_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self.scene_tree.addTopLevelItem(category_item)
            for label, prompt in scenes:
                scene_item = QTreeWidgetItem([label])
                scene_item.setData(0, Qt.ItemDataRole.UserRole, prompt)
                category_item.addChild(scene_item)
            category_item.setExpanded(True)

    def on_scene_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if item.childCount() > 0:
            return
        prompt = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(prompt, str):
            self.input_line.setText(prompt)

    def on_scene_item_activated(self, item: QTreeWidgetItem, column: int) -> None:
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return
        prompt = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(prompt, str):
            return
        self.send_scene_prompt(prompt)

    def send_scene_prompt(self, prompt: str) -> None:
        self.input_line.setText(prompt)
        self.send_current_input()

    def send_current_input(self) -> None:
        if self.is_busy:
            return
        if self.current_project is None or self.current_session is None:
            QMessageBox.information(self, "提示", "请先创建并选择一个对话。")
            return

        message = self.input_line.text().strip()
        attachments = list(self.selected_attachments)
        if not message and not attachments:
            return
        outgoing_message = self.compose_outgoing_message(message, attachments)

        session_id = self.current_session.id
        project = self.current_project
        session = self.current_session
        request_id = self.next_request_id()
        provider = self.assistant.provider_name()
        target = self.assistant.target_label()
        attachment_ids = self.persist_attachments(attachments)

        self.apply_auto_session_title(
            session_id,
            message or " ".join(path.name for path in attachments),
        )
        self.storage.add_message(
            session_id,
            "user",
            outgoing_message,
            attachment_ids=attachment_ids,
        )
        self.refresh_tree()
        if self.current_session is not None and self.current_session.id == session_id:
            self.load_session(session_id)
        self.input_line.clear()
        self.clear_selected_attachments()
        self.set_busy(True)

        self.request_contexts[request_id] = RequestContext(
            session_id=session_id,
            provider=provider,
            target=target,
            started_at=perf_counter(),
        )
        self.start_pending_response(request_id, session_id)

        recent_messages = self.storage.list_messages(session_id)[-12:]
        worker = AssistantWorker(
            self.assistant,
            project=project,
            session=session,
            recent_messages=recent_messages,
            user_message=outgoing_message,
        )
        self.worker = worker
        self.workers[request_id] = worker
        worker.streamed.connect(
            lambda content, request_session_id=session_id, current_request_id=request_id: (
                self.on_assistant_stream(current_request_id, request_session_id, content)
            )
        )
        worker.succeeded.connect(
            lambda result, request_session_id=session_id, current_request_id=request_id: (
                self.on_assistant_reply(current_request_id, request_session_id, result)
            )
        )
        worker.failed.connect(
            lambda result, request_session_id=session_id, current_request_id=request_id: (
                self.on_assistant_error(current_request_id, request_session_id, result)
            )
        )
        worker.finished.connect(
            lambda request_session_id=session_id, current_request_id=request_id: (
                self.on_request_finished(current_request_id, request_session_id)
            )
        )
        worker.start()

    def cancel_active_request(self) -> None:
        request_id = self.active_request_id
        if request_id is None:
            return

        context = self.request_contexts.get(request_id)
        session_id = context.session_id if context else self.pending_session_id
        if session_id is None:
            return

        self.canceled_request_ids.add(request_id)
        elapsed_ms = (
            int((perf_counter() - context.started_at) * 1000)
            if context is not None
            else 0
        )
        cancel_text = "【已取消】\n已停止等待本次模型回复。"
        self.storage.add_message(session_id, "assistant", cancel_text)
        if context is not None:
            self.storage.add_request_log(
                session_id=session_id,
                provider=context.provider,
                model=context.target,
                status="canceled",
                error_type="canceled",
                stream_mode="canceled",
                latency_ms=elapsed_ms,
                first_token_latency_ms=context.first_token_latency_ms,
                detail="User canceled waiting for the response.",
            )
        if self.current_session is not None and self.current_session.id == session_id:
            self.load_session(session_id)
        self.clear_pending_response(request_id, session_id)
        self.set_busy(False)
        self._set_status_message("已取消等待")

    def on_request_finished(self, request_id: int, session_id: int) -> None:
        worker = self.workers.pop(request_id, None)
        if self.worker is worker:
            self.worker = None
        self.clear_pending_response(request_id, session_id)
        self.request_contexts.pop(request_id, None)
        self.canceled_request_ids.discard(request_id)
        if self.active_request_id is None:
            self.set_busy(False)
        if self.closing_after_requests and not self.workers:
            self.close()

    def on_assistant_reply(self, request_id: int, session_id: int, result: WorkerResult) -> None:
        if request_id in self.canceled_request_ids:
            return
        self.storage.add_message(session_id, "assistant", result.content)
        self.storage.add_request_log(
            session_id=session_id,
            provider=result.provider,
            model=result.target,
            status="success",
            error_type="",
            stream_mode=result.stream_mode,
            latency_ms=result.latency_ms,
            first_token_latency_ms=result.first_token_latency_ms,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            detail="",
        )
        self.refresh_tree()
        if self.current_session is not None and self.current_session.id == session_id:
            self.load_session(session_id)
        self._set_status_message(
            f"最近一次请求 首字 {result.first_token_latency_ms} ms / 总耗时 {result.latency_ms} ms"
        )

    def on_assistant_error(self, request_id: int, session_id: int, result: WorkerResult) -> None:
        if request_id in self.canceled_request_ids:
            return
        error_text = f"【错误】\n{result.error}"
        self.storage.add_message(session_id, "assistant", error_text)
        self.storage.add_request_log(
            session_id=session_id,
            provider=result.provider,
            model=result.target,
            status="error",
            error_type=result.error_type,
            stream_mode=result.stream_mode,
            latency_ms=result.latency_ms,
            first_token_latency_ms=result.first_token_latency_ms,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            detail=result.error,
        )
        self.refresh_tree()
        if self.current_session is not None and self.current_session.id == session_id:
            self.load_session(session_id)
        QMessageBox.warning(self, "请求失败", result.error)

    def closeEvent(self, event: QCloseEvent) -> None:
        running_workers = [worker for worker in self.workers.values() if worker.isRunning()]
        if not running_workers:
            super().closeEvent(event)
            return
        self.closing_after_requests = True
        if self.active_request_id is not None:
            self.cancel_active_request()
        self.hide()
        event.ignore()


def build_main_window() -> MainWindow:
    storage = Storage()
    storage.bootstrap()
    settings = storage.get_provider_settings(provider_settings_from_env())
    assistant = AssistantService(settings)
    return MainWindow(storage=storage, assistant=assistant)


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or [])
    app.setApplicationName("DarkFactory")
    return app
