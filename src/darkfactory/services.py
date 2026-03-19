from __future__ import annotations

import json
from dataclasses import asdict
from typing import Iterable, Iterator

from .config import (
    derive_http_cancel_url,
    derive_http_health_url,
    derive_http_providers_url,
    derive_http_stream_url,
    provider_settings_from_env,
)
from .models import Message, Project, ProviderSettings, ResponseMetrics, Session


SUPPORTED_PROVIDERS = {"mock", "ollama", "openai_compatible", "http_backend"}


class AssistantService:
    def __init__(self, settings: ProviderSettings | None = None) -> None:
        self._settings = settings
        self._last_metrics = ResponseMetrics()

    def update_settings(self, settings: ProviderSettings) -> None:
        self._settings = settings

    def current_settings(self) -> ProviderSettings:
        return self._settings or provider_settings_from_env()

    def last_response_metrics(self) -> ResponseMetrics:
        return self._last_metrics

    def provider_name(self, settings: ProviderSettings | None = None) -> str:
        config = settings or self.current_settings()
        explicit = config.provider.strip().lower()
        if explicit in SUPPORTED_PROVIDERS:
            return explicit
        if config.ollama_model:
            return "ollama"
        if config.openai_base_url and config.openai_model:
            return "openai_compatible"
        if config.api_url:
            return "http_backend"
        return "mock"

    def target_label(self, settings: ProviderSettings | None = None) -> str:
        config = settings or self.current_settings()
        provider = self.provider_name(config)
        if provider == "ollama":
            return config.ollama_model or config.ollama_url
        if provider == "openai_compatible":
            return config.openai_model or config.openai_base_url
        if provider == "http_backend":
            return config.api_url
        return "mock"

    def request_timeout_seconds(self, settings: ProviderSettings | None = None) -> int:
        config = settings or self.current_settings()
        return max(5, min(int(config.request_timeout_seconds), 300))

    def mode_label(self, settings: ProviderSettings | None = None) -> str:
        config = settings or self.current_settings()
        provider = self.provider_name(config)
        if provider == "ollama":
            model = config.ollama_model or "未设置模型"
            return f"Local LLM (Ollama): {model}"
        if provider == "openai_compatible":
            model = config.openai_model or "未设置模型"
            return f"OpenAI-Compatible: {model}"
        if provider == "http_backend":
            return f"HTTP Backend: {config.api_url or '未设置地址'}"
        return "Mock"

    def reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        settings: ProviderSettings | None = None,
        client_request_id: str = "",
    ) -> str:
        return "".join(
            self.stream_reply(
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                settings=settings,
                client_request_id=client_request_id,
            )
        )

    def stream_reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        settings: ProviderSettings | None = None,
        client_request_id: str = "",
    ) -> Iterator[str]:
        config = settings or self.current_settings()
        provider = self.provider_name(config)
        timeout = float(self.request_timeout_seconds(config))
        self._last_metrics = ResponseMetrics()
        if provider == "ollama":
            self._last_metrics.stream_mode = "stream"
            yield from self._stream_via_openai_compatible(
                base_url=config.ollama_url or "http://127.0.0.1:11434/v1",
                api_key=config.ollama_api_key or "ollama",
                model=config.ollama_model,
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                timeout=timeout,
                client_request_id=client_request_id,
            )
            return
        if provider == "openai_compatible":
            self._last_metrics.stream_mode = "stream"
            yield from self._stream_via_openai_compatible(
                base_url=config.openai_base_url,
                api_key=config.openai_api_key,
                model=config.openai_model,
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                timeout=timeout,
                client_request_id=client_request_id,
            )
            return
        if provider == "http_backend":
            self._last_metrics.stream_mode = "single"
            yield self._reply_via_http(
                api_url=config.api_url,
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                timeout=timeout,
                client_request_id=client_request_id,
            )
            return
        self._last_metrics.stream_mode = "stream"
        yield from self._stream_via_mock(project=project, user_message=user_message)

    def health_check(self, settings: ProviderSettings | None = None) -> str:
        config = settings or self.current_settings()
        provider = self.provider_name(config)
        timeout = min(15.0, float(self.request_timeout_seconds(config)))
        if provider == "mock":
            return "Mock provider is available."
        if provider in {"ollama", "openai_compatible"}:
            base_url = config.ollama_url if provider == "ollama" else config.openai_base_url
            api_key = config.ollama_api_key if provider == "ollama" else config.openai_api_key
            if not base_url:
                raise ValueError("Provider requires a base URL")
            endpoint = base_url.rstrip("/") + "/models"
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            import httpx

            with httpx.Client(timeout=timeout) as client:
                response = client.get(endpoint, headers=headers)
                response.raise_for_status()
            data = response.json()
            models = data.get("data") or []
            return f"Connected successfully. Models visible: {len(models)}"
        if provider == "http_backend":
            health_url = derive_http_health_url(config.api_url, config.api_health_url)
            if not health_url:
                raise ValueError("HTTP backend requires api_url or api_health_url")
            import httpx

            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(health_url)
                response.raise_for_status()
            return f"Connected successfully: {health_url}"
        raise ValueError(f"Unsupported provider: {provider}")

    def gateway_capabilities(self, settings: ProviderSettings | None = None) -> dict[str, str]:
        config = settings or self.current_settings()
        return {
            "chat_url": config.api_url,
            "stream_url": derive_http_stream_url(config.api_url, config.api_stream_url),
            "health_url": derive_http_health_url(config.api_url, config.api_health_url),
            "providers_url": derive_http_providers_url(
                config.api_url,
                config.api_providers_url,
            ),
            "cancel_url_template": (
                config.api_cancel_url_template.strip()
                or derive_http_cancel_url(config.api_url, "{request_id}")
            ),
        }

    def cancel_request(self, request_id: str, settings: ProviderSettings | None = None) -> str:
        config = settings or self.current_settings()
        provider = self.provider_name(config)
        if provider != "http_backend":
            raise ValueError("Server-side cancel is currently reserved for http_backend")

        cancel_url = derive_http_cancel_url(
            config.api_url,
            request_id,
            config.api_cancel_url_template,
        )
        if not cancel_url:
            raise ValueError("HTTP backend cancel URL is not configured")

        import httpx

        timeout = min(10.0, float(self.request_timeout_seconds(config)))
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(cancel_url, json={"request_id": request_id})
            response.raise_for_status()
        return cancel_url

    def _reply_via_http(
        self,
        *,
        api_url: str,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        timeout: float,
        client_request_id: str,
    ) -> str:
        if not api_url:
            raise ValueError("HTTP backend provider requires api_url")
        payload = {
            "project": asdict(project),
            "session": asdict(session),
            "recent_messages": [asdict(message) for message in recent_messages],
            "message": user_message,
        }
        import httpx

        headers = {"X-Client-Request-Id": client_request_id} if client_request_id else {}
        with httpx.Client(timeout=timeout) as client:
            response = client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
        data = response.json()
        self._apply_usage_metrics(data.get("usage") or {})
        reply = data.get("reply", "").strip()
        if not reply:
            raise ValueError("HTTP assistant response did not contain 'reply'")
        return reply

    def _reply_via_openai_compatible(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        timeout: float,
        client_request_id: str,
    ) -> str:
        if not base_url:
            raise ValueError("OpenAI-compatible provider requires base_url")
        if not model:
            raise ValueError("OpenAI-compatible provider requires model")

        return "".join(
            self._stream_via_openai_compatible(
                base_url=base_url,
                api_key=api_key,
                model=model,
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
                timeout=timeout,
                client_request_id=client_request_id,
            )
        )

    def _stream_via_openai_compatible(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
        timeout: float,
        client_request_id: str,
    ) -> Iterator[str]:
        if not base_url:
            raise ValueError("OpenAI-compatible provider requires base_url")
        if not model:
            raise ValueError("OpenAI-compatible provider requires model")

        import httpx

        messages = self._build_provider_messages(
            project=project,
            session=session,
            recent_messages=recent_messages,
            user_message=user_message,
        )

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if client_request_id:
            headers["X-Client-Request-Id"] = client_request_id

        endpoint = base_url.rstrip("/") + "/chat/completions"
        collected_parts: list[str] = []
        with httpx.Client(timeout=timeout) as client:
            with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    stripped = line.strip()
                    if not stripped.startswith("data:"):
                        continue
                    data_line = stripped[5:].strip()
                    if data_line == "[DONE]":
                        break
                    try:
                        chunk_payload = json.loads(data_line)
                    except json.JSONDecodeError:
                        continue
                    self._apply_usage_metrics(chunk_payload.get("usage") or {})
                    text = self._extract_openai_stream_text(chunk_payload)
                    if text:
                        collected_parts.append(text)
                        yield text

        if collected_parts:
            return

        fallback_payload = {
            "model": model,
            "messages": messages,
        }
        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, json=fallback_payload, headers=headers)
            response.raise_for_status()
        data = response.json()
        self._last_metrics.stream_mode = "single"
        self._apply_usage_metrics(data.get("usage") or {})
        text = self._extract_openai_response_text(data)
        if not text:
            raise ValueError("OpenAI-compatible response did not contain assistant text")
        yield text

    def _apply_usage_metrics(self, usage: dict) -> None:
        if not isinstance(usage, dict):
            return
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        if isinstance(prompt_tokens, int):
            self._last_metrics.prompt_tokens = prompt_tokens
        if isinstance(completion_tokens, int):
            self._last_metrics.completion_tokens = completion_tokens
        if isinstance(total_tokens, int):
            self._last_metrics.total_tokens = total_tokens

    def _extract_openai_stream_text(self, data: dict) -> str:
        choices = data.get("choices") or []
        if not choices:
            return ""
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""

    def _extract_openai_response_text(self, data: dict) -> str:
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            if parts:
                return "\n".join(parts)
        return ""

    def _build_provider_messages(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
    ) -> list[dict[str, str]]:
        recent_messages_list = list(recent_messages)
        system_message = (
            "你是电力能源运行分析助手。"
            "请结合项目上下文回答，并尽量使用以下结构输出："
            "【结论】【原因分析】【优化建议】【影响评估】。"
        )
        context_message = (
            f"项目名称：{project.name}\n"
            f"电厂：{project.plant or '未设置'}\n"
            f"机组：{project.unit or '未设置'}\n"
            f"专家类型：{project.expert_type or '未设置'}\n"
            f"当前对话：{session.name}"
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_message},
            {"role": "system", "content": context_message},
        ]
        for message in recent_messages_list:
            if message.role not in {"user", "assistant"}:
                continue
            messages.append({"role": message.role, "content": message.content})
        if not recent_messages_list:
            messages.append({"role": "user", "content": user_message})
        elif messages[-1]["role"] != "user" or messages[-1]["content"] != user_message:
            messages.append({"role": "user", "content": user_message})
        return messages

    def _reply_via_mock(self, *, project: Project, user_message: str) -> str:
        prompt = user_message.strip()
        project_context = " / ".join(
            part for part in (project.plant, project.unit, project.expert_type) if part
        )
        if not project_context:
            project_context = "未配置项目上下文"

        if "蒸汽" in prompt:
            conclusion = "当前蒸汽系统存在阶段性供需偏紧的迹象。"
            reasons = [
                f"当前项目上下文为：{project_context}",
                "抽汽侧需求上升会直接压缩机组可调余量",
                "如果锅炉负荷已接近上限，系统缓冲空间会明显下降",
                "当前版本未接入实时点位，结论基于行业经验模板",
            ]
            actions = [
                "优先检查高抽汽会话对应机组是否存在可回调空间",
                "核对锅炉主汽量、供汽压力和重点用户负荷变化",
                "将高优先级供汽对象单独列出，避免平均分配蒸汽",
            ]
            impact = "建议先作为运行会前分析参考，再结合现场数据确认调节幅度。"
        elif "负荷" in prompt:
            conclusion = "当前问题更适合从负荷分配和运行方式切换上优化。"
            reasons = [
                f"当前项目上下文为：{project_context}",
                "单机负荷过高会抬高边际煤耗和运行风险",
                "负荷分配不均可能放大抽汽与发电之间的冲突",
                "第一版尚未接入历史效率曲线，因此无法给出精确数值",
            ]
            actions = [
                "比较各机组当前负荷与经济区间的偏差",
                "优先把波动负荷分配给调节性能更好的机组",
                "结合值班目标决定是优先保供汽还是优先提发电",
            ]
            impact = "如果后续接入实时与历史数据，可进一步输出具体负荷建议值。"
        else:
            conclusion = "当前问题可以先按能效与运行约束两个维度组织分析。"
            reasons = [
                f"当前项目上下文为：{project_context}",
                "管理人员更关心结果与影响，技术人员更关心约束与原因",
                "第一版优先验证工作台与对话流，不追求复杂推理",
                "会话已按项目归档，适合持续积累专题分析记录",
            ]
            actions = [
                "明确本次分析目标，是保供、提效还是稳态运行",
                "把关键工况、约束和期望结果写进当前会话",
                "使用快捷按钮先生成结构化结论，再人工补充追问",
            ]
            impact = "适合先用于结构化沟通和问题收敛，再逐步接入更强的数据分析能力。"

        reasons_text = "\n".join(f"{index}. {item}" for index, item in enumerate(reasons, start=1))
        actions_text = "\n".join(f"{index}. {item}" for index, item in enumerate(actions, start=1))
        return (
            f"【项目】\n{project.name}\n\n"
            f"【结论】\n{conclusion}\n\n"
            f"【原因分析】\n{reasons_text}\n\n"
            f"【优化建议】\n{actions_text}\n\n"
            f"【影响评估】\n{impact}"
        )

    def _stream_via_mock(self, *, project: Project, user_message: str) -> Iterator[str]:
        reply = self._reply_via_mock(project=project, user_message=user_message)
        segments = reply.split("\n\n")
        for index, segment in enumerate(segments):
            if index > 0:
                yield "\n\n"
            yield segment
