#!/usr/bin/env python3
"""Normalize Windows OCR output into page-aware private RAG artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


KEYWORDS = [
    "书写速度",
    "书写力度",
    "笔压",
    "倾斜",
    "字间距",
    "行间距",
    "连笔",
    "布局",
    "结构",
    "笔画",
    "心理",
    "综合分析",
    "保密",
]


def normalize(text: str) -> str:
    text = text.replace("\r", "\n").replace("\u3000", " ")
    text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    text = re.sub(r"\s+([，。！？；：、）》」】）])", r"\1", text)
    text = re.sub(r"([《「【（])\s+", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_chunks(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    if not text:
        return []
    values: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = max(text.rfind("。", start, end), text.rfind("；", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        value = text[start:end].strip()
        if value:
            values.append(value)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="整理《笔迹心理学》OCR知识库")
    parser.add_argument(
        "--ocr", type=Path, default=Path("references/private/handwriting-book/ocr_raw.jsonl")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("references/private/handwriting-book")
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pages: list[dict[str, object]] = []
    with args.ocr.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            pages.append(
                {
                    "pdfPage": int(record["pdfPage"]),
                    "text": normalize(str(record.get("text", ""))),
                }
            )
    pages.sort(key=lambda row: int(row["pdfPage"]))

    source_hash = hashlib.sha256(args.ocr.read_bytes()).hexdigest()
    keyword_pages: dict[str, list[int]] = defaultdict(list)
    candidates: list[dict[str, object]] = []
    chunk_count = 0
    with (args.output_dir / "pages.jsonl").open("w", encoding="utf-8") as page_handle, (
        args.output_dir / "chunks.jsonl"
    ).open("w", encoding="utf-8") as chunk_handle:
        for page in pages:
            page_number = int(page["pdfPage"])
            text = str(page["text"])
            page_handle.write(
                json.dumps(
                    {"source": "笔迹心理学.pdf", "pdfPage": page_number, "text": text},
                    ensure_ascii=False,
                )
                + "\n"
            )
            for index, value in enumerate(split_chunks(text), start=1):
                chunk_count += 1
                chunk_handle.write(
                    json.dumps(
                        {
                            "chunkId": f"book-p{page_number:03d}-c{index:02d}",
                            "source": "笔迹心理学.pdf",
                            "pdfPage": page_number,
                            "text": value,
                            "usage": "hypothesis_only_not_diagnostic_label",
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            for keyword in KEYWORDS:
                if keyword in text:
                    keyword_pages[keyword].append(page_number)
                    position = text.find(keyword)
                    candidates.append(
                        {
                            "keyword": keyword,
                            "pdf_page": page_number,
                            "context": text[max(0, position - 80) : position + 180],
                            "review_status": "pending_manual_review",
                        }
                    )

    with (args.output_dir / "review_candidates.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["keyword", "pdf_page", "context", "review_status"]
        )
        writer.writeheader()
        writer.writerows(candidates)

    index = {
        "source": "笔迹心理学.pdf",
        "ocrSha256": source_hash,
        "pages": len(pages),
        "pagesWithText": sum(bool(page["text"]) for page in pages),
        "totalCharacters": sum(len(str(page["text"])) for page in pages),
        "chunks": chunk_count,
        "keywordPages": dict(keyword_pages),
        "safety": "OCR content supplies hypotheses only and cannot create ground-truth labels.",
    }
    (args.output_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(index, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
