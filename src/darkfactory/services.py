from __future__ import annotations

import os
from dataclasses import asdict
from typing import Iterable

from .models import Message, Project, Session


class AssistantService:
    def provider_name(self) -> str:
        explicit = os.getenv("DARKFACTORY_LLM_PROVIDER", "").strip().lower()
        if explicit in {"mock", "ollama", "openai_compatible", "http_backend"}:
            return explicit

        if os.getenv("DARKFACTORY_OLLAMA_MODEL", "").strip():
            return "ollama"
        if os.getenv("DARKFACTORY_OPENAI_BASE_URL", "").strip() and os.getenv(
            "DARKFACTORY_OPENAI_MODEL", ""
        ).strip():
            return "openai_compatible"
        if os.getenv("DARKFACTORY_API_URL", "").strip():
            return "http_backend"
        return "mock"

    def mode_label(self) -> str:
        provider = self.provider_name()
        if provider == "ollama":
            model = os.getenv("DARKFACTORY_OLLAMA_MODEL", "").strip() or "未设置模型"
            return f"Local LLM (Ollama): {model}"
        if provider == "openai_compatible":
            model = os.getenv("DARKFACTORY_OPENAI_MODEL", "").strip() or "未设置模型"
            return f"OpenAI-Compatible: {model}"
        if provider == "http_backend":
            api_url = os.getenv("DARKFACTORY_API_URL", "").strip()
            return f"HTTP Backend: {api_url}"
        return "Mock"

    def reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
    ) -> str:
        provider = self.provider_name()
        if provider == "ollama":
            return self._reply_via_openai_compatible(
                base_url=os.getenv("DARKFACTORY_OLLAMA_URL", "").strip()
                or "http://127.0.0.1:11434/v1",
                api_key=os.getenv("DARKFACTORY_OLLAMA_API_KEY", "").strip() or "ollama",
                model=os.getenv("DARKFACTORY_OLLAMA_MODEL", "").strip(),
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
            )
        if provider == "openai_compatible":
            return self._reply_via_openai_compatible(
                base_url=os.getenv("DARKFACTORY_OPENAI_BASE_URL", "").strip(),
                api_key=os.getenv("DARKFACTORY_OPENAI_API_KEY", "").strip(),
                model=os.getenv("DARKFACTORY_OPENAI_MODEL", "").strip(),
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
            )
        if provider == "http_backend":
            return self._reply_via_http(
                api_url=os.getenv("DARKFACTORY_API_URL", "").strip(),
                project=project,
                session=session,
                recent_messages=recent_messages,
                user_message=user_message,
            )
        return self._reply_via_mock(project=project, user_message=user_message)

    def _reply_via_http(
        self,
        *,
        api_url: str,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
    ) -> str:
        payload = {
            "project": asdict(project),
            "session": asdict(session),
            "recent_messages": [asdict(message) for message in recent_messages],
            "message": user_message,
        }
        import httpx

        with httpx.Client(timeout=20.0) as client:
            response = client.post(api_url, json=payload)
            response.raise_for_status()
        data = response.json()
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
    ) -> str:
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
        }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        endpoint = base_url.rstrip("/") + "/chat/completions"
        with httpx.Client(timeout=60.0) as client:
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
        data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise ValueError("OpenAI-compatible response did not contain choices")
        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content.strip()

        # Some compatible backends may return structured content arrays.
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            if parts:
                return "\n".join(parts)

        raise ValueError("OpenAI-compatible response did not contain assistant text")

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
            impact = "该回答来自本地 mock 模式，可在接入后端后替换为真实分析结果。"

        formatted_reasons = "\n".join(
            f"{index}. {item}" for index, item in enumerate(reasons, start=1)
        )
        formatted_actions = "\n".join(
            f"{index}. {item}" for index, item in enumerate(actions, start=1)
        )

        return (
            f"【项目】\n{project.name}\n\n"
            f"【结论】\n{conclusion}\n\n"
            f"【原因分析】\n{formatted_reasons}\n\n"
            f"【优化建议】\n{formatted_actions}\n\n"
            f"【影响评估】\n{impact}"
        )
