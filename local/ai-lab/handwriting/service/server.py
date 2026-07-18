"""Dependency-free local HTTP service for the MindLine handwriting module."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from analyzer import BASELINE_PREDICTOR, TraceValidationError, analyse_trace
from llm import HandwritingLlmExplainer


SERVICE_DIR = Path(__file__).resolve().parent
COLLECTOR_DIR = SERVICE_DIR.parent / "collector"
LLM_EXPLAINER = HandwritingLlmExplainer()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(SERVICE_DIR), **kwargs)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._json(204, {})

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/collector", "/collector/"):
            self.directory = str(COLLECTOR_DIR)
            self.path = "/index.html"
        elif self.path.startswith("/collector/"):
            self.directory = str(COLLECTOR_DIR)
            self.path = self.path.removeprefix("/collector")
        if self.path in ("/health", "/api/v1/health"):
            self._json(
                200,
                {
                    "status": "UP",
                    "module": "handwriting",
                    "version": "0.4.0",
                    "llm": LLM_EXPLAINER.health(),
                    "baseline": BASELINE_PREDICTOR.health(),
                },
            )
            return
        if self.path == "/":
            self.path = "/demo.html"
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ("/handwriting/analyze", "/api/v1/handwriting/analyze"):
            self._json(404, _envelope(False, "NOT_FOUND", "接口不存在", None, None))
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 20 * 1024 * 1024:
                raise TraceValidationError("请求体为空或超过 20MB 限制")
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(request, dict):
                raise TraceValidationError("请求体必须是 JSON 对象")
            request_id = request.get("requestId")
            trace = request.get("trace", request)
            result = analyse_trace(trace, request_id)
            if request.get("includeLlm", True):
                result["llmExplanation"] = LLM_EXPLAINER.explain(result)
            self._json(200, _envelope(True, "OK", "分析完成", result, result["requestId"]))
        except (TraceValidationError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self._json(400, _envelope(False, "HANDWRITING_INVALID_TRACE", str(error), None, None))
        except Exception as error:  # keep local demo alive and return a stable envelope
            self._json(500, _envelope(False, "HANDWRITING_ANALYSIS_FAILED", str(error), None, None))


def _envelope(success: bool, code: str, message: str, data: Any, request_id: str | None) -> dict[str, Any]:
    return {
        "success": success,
        "code": code,
        "message": message,
        "data": data,
        "requestId": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="启动心迹AI笔迹分析本地服务")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8090, type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Handwriting service: http://127.0.0.1:{args.port}")
    print(f"Result demo:        http://127.0.0.1:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
