from __future__ import annotations

import os
from dataclasses import asdict
from typing import Iterable

from .models import Message, Project, Session


class AssistantService:
    def reply(
        self,
        *,
        project: Project,
        session: Session,
        recent_messages: Iterable[Message],
        user_message: str,
    ) -> str:
        api_url = os.getenv("DARKFACTORY_API_URL", "").strip()
        if api_url:
            return self._reply_via_http(
                api_url=api_url,
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

    def _reply_via_mock(self, *, project: Project, user_message: str) -> str:
        prompt = user_message.strip()

        if "蒸汽" in prompt:
            conclusion = "当前蒸汽系统存在阶段性供需偏紧的迹象。"
            reasons = [
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
