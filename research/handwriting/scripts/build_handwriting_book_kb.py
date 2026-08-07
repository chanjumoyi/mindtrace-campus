#!/usr/bin/env python3
"""Extract a local PDF into page-aware private JSONL chunks for RAG."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


def normalize(text: str) -> str:
    text = text.replace("\u3000", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunks(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text] if text else []
    result: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = max(text.rfind("。", start, end), text.rfind("\n", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        value = text[start:end].strip()
        if value:
            result.append(value)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="构建《笔迹心理学》本地RAG知识库")
    parser.add_argument("pdf", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research/handwriting/private/knowledge"),
    )
    parser.add_argument("--chunk-size", type=int, default=900)
    parser.add_argument("--overlap", type=int, default=120)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(args.pdf))
    source_hash = hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    page_path = args.output_dir / "pages.jsonl"
    chunk_path = args.output_dir / "chunks.jsonl"
    page_char_counts: list[int] = []
    chunk_count = 0
    with page_path.open("w", encoding="utf-8") as page_handle, chunk_path.open(
        "w", encoding="utf-8"
    ) as chunk_handle:
        for page_index, page in enumerate(reader.pages, start=1):
            text = normalize(page.extract_text() or "")
            page_char_counts.append(len(text))
            page_handle.write(
                json.dumps(
                    {
                        "source": args.pdf.name,
                        "sourceSha256": source_hash,
                        "pdfPage": page_index,
                        "text": text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            for local_index, value in enumerate(
                chunks(text, args.chunk_size, args.overlap), start=1
            ):
                chunk_count += 1
                chunk_handle.write(
                    json.dumps(
                        {
                            "chunkId": f"book-p{page_index:03d}-c{local_index:02d}",
                            "source": args.pdf.name,
                            "sourceSha256": source_hash,
                            "pdfPage": page_index,
                            "text": value,
                            "usage": "hypothesis_only_not_diagnostic_label",
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    nonempty = sum(count > 0 for count in page_char_counts)
    result = {
        "source": str(args.pdf.resolve()),
        "sourceSha256": source_hash,
        "pages": len(page_char_counts),
        "pagesWithExtractedText": nonempty,
        "textCoverage": round(nonempty / len(page_char_counts), 4),
        "totalCharacters": sum(page_char_counts),
        "medianCharactersPerPage": sorted(page_char_counts)[len(page_char_counts) // 2],
        "chunks": chunk_count,
        "requiresOcr": nonempty < len(page_char_counts) * 0.8,
        "safety": "Book content is a hypothesis source, not ground-truth psychological labels.",
    }
    (args.output_dir / "index.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
