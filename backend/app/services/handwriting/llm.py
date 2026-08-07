"""Safe Qwen/OpenAI-compatible explanation layer for handwriting observations."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.client import RemoteDisconnected
from typing import Any

DISCLAIMER = "笔迹结果仅用于观察本次书写行为和自我探索，不构成心理评估、人格判断或医学诊断。"
FORBIDDEN_TERMS = ("诊断为", "患有", "人格障碍", "心理疾病", "抑郁症", "焦虑症", "精神疾病")


@dataclass(frozen=True)
class LlmConfig:
    mode: str
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int
    max_attempts: int = 3

    @classmethod
    def from_env(cls) -> LlmConfig:
        return cls(
            mode=os.getenv("HANDWRITING_LLM_MODE", "mock").strip().lower(),
            api_key=(os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or "").strip(),
            base_url=os.getenv(
                "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ).strip(),
            model=os.getenv("QWEN_MODEL", "qwen2.5-7b-instruct").strip(),
            timeout_seconds=int(os.getenv("QWEN_TIMEOUT_SECONDS", "20")),
            max_attempts=max(1, min(5, int(os.getenv("QWEN_MAX_ATTEMPTS", "3")))),
        )


class HandwritingLlmExplainer:
    def __init__(self, config: LlmConfig | None = None) -> None:
        self.config = config or LlmConfig.from_env()

    def health(self) -> dict[str, Any]:
        configured = self.config.mode == "qwen" and bool(
            self.config.api_key and self.config.base_url
        )
        return {
            "mode": self.config.mode,
            "provider": "qwen" if self.config.mode == "qwen" else "mock",
            "model": self.config.model if self.config.mode == "qwen" else "deterministic-mock",
            "configured": configured if self.config.mode == "qwen" else True,
            "maxAttempts": self.config.max_attempts,
        }

    def explain(self, analysis: dict[str, Any]) -> dict[str, Any]:
        if self.config.mode != "qwen":
            return self._mock(analysis, "MOCK", "本地 Mock 模式，尚未调用外部模型。")
        if not self.config.api_key or not self.config.base_url:
            return self._mock(analysis, "DEGRADED", "Qwen 未配置 API Key 或 Base URL，已安全降级。")
        try:
            result = self._call_qwen_with_retry(analysis)
            result.update(
                {
                    "status": "SUCCESS",
                    "provider": "qwen",
                    "model": self.config.model,
                    "degradationNote": None,
                }
            )
            return result
        # Any upstream transport or response-shape failure must not discard the
        # already-computed local analysis. Keep the public error detail generic.
        except Exception as error:
            detail = self._safe_error_detail(error)
            return self._mock(
                analysis,
                "DEGRADED",
                f"Qwen 调用失败，已安全降级：{detail}（最多尝试 {self.config.max_attempts} 次）",
            )

    def _call_qwen_with_retry(self, analysis: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return self._call_qwen(analysis)
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == self.config.max_attempts:
                    raise
            except (RemoteDisconnected, ConnectionError, TimeoutError, urllib.error.URLError):
                if attempt == self.config.max_attempts:
                    raise
            time.sleep(0.35 * attempt)
        raise RuntimeError("Qwen retry loop exhausted")

    @staticmethod
    def _safe_error_detail(error: Exception) -> str:
        if isinstance(error, urllib.error.HTTPError):
            return f"HTTP {error.code}"
        return type(error).__name__

    def _call_qwen(self, analysis: dict[str, Any]) -> dict[str, Any]:
        evidence = {
            "observations": analysis.get("observations", []),
            "dataQuality": analysis.get("dataQuality"),
            "confidence": analysis.get("confidence"),
            "citations": analysis.get("citations", []),
            "limitations": analysis.get("limitations", [])[:4],
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位温和而专业的大学生书写行为观察员。你的任务是帮助用户通过书写特征来进行自我探索。\n"
                    "请做到以下几点：\n"
                    "1. 用温暖、自然的语言描述这次书写行为的特点，像一个耐心的老师或辅导员在交流，而不是播报统计数据。\n"
                    "2. 将数据转化为有意义的观察——例如速度快慢反映了怎样的书写状态，停顿可能意味着什么。\n"
                    "3. 提出2-3个真正能引发用户思考的开放性问题。\n"
                    "4. summary 控制在150字以内，语气亲切但不越界。\n"
                    "安全边界（必须遵守）：\n"
                    "- 不得从笔迹推断人格、情绪障碍、心理健康状况或疾病。\n"
                    "- 不得给出诊断、治疗建议或医学判断。\n"
                    "- 只能说「可能反映」「或许意味着」等推测性表达，不能说「你有」「你患有」。\n"
                    "输出严格 JSON，字段为 summary、explorationQuestions（2至3个开放问题）、disclaimer。不要输出 Markdown。"
                ),
            },
            {
                "role": "user",
                "content": "请基于以下书写行为数据，生成一段温暖的自然语言分析：\n"
                + json.dumps(evidence, ensure_ascii=False),
            },
        ]
        body = json.dumps(
            {
                "model": self.config.model,
                "messages": messages,
                "temperature": 0.6,
                "max_tokens": 700,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self.config.base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Connection": "close",
                "User-Agent": "MindLine-Handwriting/0.4",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        parsed = self._parse_json(content)
        summary = str(parsed.get("summary", "")).strip()
        questions = [
            str(item).strip()
            for item in parsed.get("explorationQuestions", [])
            if str(item).strip()
        ]
        if not summary or not 2 <= len(questions) <= 3:
            raise ValueError("Qwen response does not match the required schema")
        combined = summary + " " + " ".join(questions)
        if any(term in combined for term in FORBIDDEN_TERMS):
            raise ValueError("Qwen response crossed the medical safety boundary")
        return {"summary": summary, "explorationQuestions": questions, "disclaimer": DISCLAIMER}

    @staticmethod
    def _parse_json(content: Any) -> dict[str, Any]:
        text = str(content).strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("LLM output must be a JSON object")
        return value

    def _mock(self, analysis: dict[str, Any], status: str, note: str) -> dict[str, Any]:
        observations = analysis.get("observations") or []
        descriptions = [
            str(item.get("description", "")) for item in observations[:3] if item.get("description")
        ]
        summary = (
            "本次记录的客观特征包括：" + "；".join(descriptions)
            if descriptions
            else "当前数据不足以形成稳定的客观摘要。"
        )
        return {
            "status": status,
            "provider": "mock",
            "model": "deterministic-mock",
            "summary": summary,
            "explorationQuestions": [
                "这次书写过程中，哪些位置让你感觉最流畅或最需要停下来思考？",
                "如果在相同设备和任务下再次书写，你觉得哪些习惯可能保持不变？",
            ],
            "disclaimer": DISCLAIMER,
            "degradationNote": note,
        }
