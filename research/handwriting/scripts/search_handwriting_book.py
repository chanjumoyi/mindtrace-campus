#!/usr/bin/env python3
"""Small local lexical retriever for the private handwriting-book RAG chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def pdf_page(value: object) -> int:
    """Sort key helper: a missing or non-numeric page must not crash the search."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="检索《笔迹心理学》本地OCR知识库")
    parser.add_argument("query", help="用空格分隔关键词，例如：书写速度 下笔重 综合分析")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--chunks",
        type=Path,
        default=Path("research/handwriting/private/knowledge/chunks.jsonl"),
    )
    args = parser.parse_args()
    terms = [term.strip() for term in args.query.split() if term.strip()]
    if not terms:
        parser.error("至少提供一个关键词")
    if not args.chunks.is_file():
        parser.error(f"未找到本地知识库分块文件：{args.chunks}；请先构建知识库")

    results: list[tuple[int, dict[str, object]]] = []
    try:
        with args.chunks.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    parser.error(f"{args.chunks}:{line_number} 不是合法 JSON：{error}")
                if not isinstance(record, dict):
                    parser.error(f"{args.chunks}:{line_number} 不是 JSON 对象")
                text = str(record.get("text", ""))
                matched = {term: text.count(term) for term in terms if term in text}
                if not matched:
                    continue
                score = sum(count * 2 for count in matched.values()) + len(matched) * 3
                results.append(
                    (
                        score,
                        {
                            "chunkId": record.get("chunkId"),
                            "pdfPage": record.get("pdfPage"),
                            "score": score,
                            "matchedTerms": matched,
                            "text": text,
                            "usage": record.get("usage"),
                        },
                    )
                )
    except OSError as error:
        parser.error(f"无法读取 {args.chunks}：{error}")
    results.sort(key=lambda item: (-item[0], pdf_page(item[1]["pdfPage"])))
    print(json.dumps([item[1] for item in results[: args.top_k]], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
