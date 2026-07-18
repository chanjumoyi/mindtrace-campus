#!/usr/bin/env python3
"""Small local lexical retriever for the private handwriting-book RAG chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="检索《笔迹心理学》本地OCR知识库")
    parser.add_argument("query", help="用空格分隔关键词，例如：书写速度 下笔重 综合分析")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--chunks",
        type=Path,
        default=Path("references/private/handwriting-book/chunks.jsonl"),
    )
    args = parser.parse_args()
    terms = [term.strip() for term in args.query.split() if term.strip()]
    if not terms:
        parser.error("至少提供一个关键词")

    results: list[tuple[int, dict[str, object]]] = []
    with args.chunks.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            text = str(record.get("text", ""))
            matched = {term: text.count(term) for term in terms if term in text}
            if not matched:
                continue
            score = sum(count * 2 for count in matched.values()) + len(matched) * 3
            results.append(
                (
                    score,
                    {
                        "chunkId": record["chunkId"],
                        "pdfPage": record["pdfPage"],
                        "score": score,
                        "matchedTerms": matched,
                        "text": text,
                        "usage": record["usage"],
                    },
                )
            )
    results.sort(key=lambda item: (-item[0], int(item[1]["pdfPage"])))
    print(json.dumps([item[1] for item in results[: args.top_k]], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
