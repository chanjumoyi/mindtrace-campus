"""Supportive, non-diagnostic AI companion conversation.

The module keeps the platform's safety contract in one place:

* crisis language always short-circuits to a fixed, human-reviewed referral reply;
* the external model is optional and never required, because ``LLM_MODE=mock``
  (the default) answers deterministically with no network access or secret;
* any upstream transport, shape or safety failure degrades to the mock reply
  instead of surfacing an error to a distressed user.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.client import RemoteDisconnected
from typing import Any

from ..core.config import settings

DISCLAIMER = "本平台提供心理健康教育和日常支持，不构成医学诊断，也不替代专业咨询或治疗。"
CRISIS_TERMS = ("自杀", "不想活", "结束生命", "伤害自己", "伤害别人")
CRISIS_REPLY = (
    "我很重视你刚才表达的危险信号。请先离开可能造成伤害的物品，联系可信任的人陪伴你，"
    "并立即联系学校心理中心、当地急救或报警服务。"
)
MOCK_REPLY = (
    "谢谢你愿意说出来。你可以再描述一下，这件事最近最让你难受的部分是什么？"
    "我们可以一起把感受和可行动的一小步理清。"
)
# A model reply that crosses these boundaries is discarded in favour of the mock reply.
FORBIDDEN_TERMS = ("诊断为", "患有", "人格障碍", "心理疾病", "抑郁症", "焦虑症", "精神疾病")

SYSTEM_PROMPT = (
    "你是心迹AI，一位面向大学生的支持性陪伴助手。\n"
    "1. 先用一两句话回应对方的感受，再提出一个温和、开放的追问。\n"
    "2. 只做情绪支持与自我觉察，不给出诊断、用药或治疗方案。\n"
    "3. 不臆测对方未提及的经历，不评判，不下结论。\n"
    "4. 回复控制在 150 字以内，使用自然的简体中文。\n"
    "如果对方表达自伤、伤人或紧迫危险，必须建议立即联系可信任的人、学校心理中心或当地急救服务。"
)


@dataclass(frozen=True)
class ChatReply:
    reply: str
    risk_level: str
    disclaimer: str = DISCLAIMER
    provider: str = "mock"
    model: str = "deterministic-mock"
    degradation_note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "risk_level": self.risk_level,
            "disclaimer": self.disclaimer,
            "provider": self.provider,
            "model": self.model,
            "degradation_note": self.degradation_note,
        }


def detect_crisis(message: str) -> bool:
    return any(term in message for term in CRISIS_TERMS)


class SupportiveChatService:
    """Deterministic mock by default; DeepSeek-compatible HTTP only when configured."""

    def __init__(
        self,
        mode: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        max_attempts: int | None = None,
    ) -> None:
        self.mode = (mode if mode is not None else settings.llm_mode).strip().lower()
        self.api_key = (api_key if api_key is not None else settings.llm_api_key).strip()
        self.base_url = (base_url if base_url is not None else settings.llm_base_url).strip()
        self.model = (model if model is not None else settings.llm_model).strip()
        self.timeout_seconds = timeout_seconds or settings.llm_timeout_seconds
        self.max_attempts = max_attempts or settings.llm_max_attempts

    def health(self) -> dict[str, Any]:
        configured = bool(self.mode == "llm" and self.api_key and self.base_url)
        return {
            "mode": self.mode,
            "provider": "llm" if configured else "mock",
            "model": self.model if configured else "deterministic-mock",
            "configured": configured if self.mode == "llm" else True,
            "maxAttempts": self.max_attempts,
        }

    def reply(self, message: str) -> ChatReply:
        text = message.strip()
        if detect_crisis(text):
            return ChatReply(reply=CRISIS_REPLY, risk_level="urgent_review")
        if self.mode != "llm":
            return ChatReply(reply=MOCK_REPLY, risk_level="routine")
        if not self.api_key or not self.base_url:
            return ChatReply(
                reply=MOCK_REPLY,
                risk_level="routine",
                degradation_note="未配置 LLM_API_KEY 或 LLM_BASE_URL，已安全降级为本地回复。",
            )
        try:
            reply = self._call_with_retry(text)
        except Exception as error:  # any upstream failure must not lose the user's turn
            return ChatReply(
                reply=MOCK_REPLY,
                risk_level="routine",
                degradation_note=(
                    f"LLM 调用失败，已安全降级：{self._safe_error_detail(error)}"
                    f"（最多尝试 {self.max_attempts} 次）"
                ),
            )
        return ChatReply(reply=reply, risk_level="routine", provider="llm", model=self.model)

    @staticmethod
    def _safe_error_detail(error: Exception) -> str:
        if isinstance(error, urllib.error.HTTPError):
            return f"HTTP {error.code}"
        return type(error).__name__

    def _call_with_retry(self, message: str) -> str:
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._call(message)
            except urllib.error.HTTPError as error:
                if not (error.code == 429 or error.code >= 500) or attempt == self.max_attempts:
                    raise
            except (RemoteDisconnected, ConnectionError, TimeoutError, urllib.error.URLError):
                if attempt == self.max_attempts:
                    raise
            time.sleep(0.35 * attempt)
        raise RuntimeError("LLM retry loop exhausted")

    def _call(self, message: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                "temperature": 0.6,
                "max_tokens": 500,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Connection": "close",
                "User-Agent": "MindLine-Companion/0.1",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = str(payload["choices"][0]["message"]["content"]).strip()
        if not content:
            raise ValueError("LLM returned an empty reply")
        if any(term in content for term in FORBIDDEN_TERMS):
            raise ValueError("LLM reply crossed the medical safety boundary")
        return content


chat_service = SupportiveChatService()
