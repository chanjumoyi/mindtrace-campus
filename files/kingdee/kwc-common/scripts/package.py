#!/usr/bin/env python3
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
dist = root / "dist"
out_dir = root.parents[1] / "deliverables" / "package"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / "xinji-kwc-common-1.0.0.zip"
with ZipFile(out, "w", ZIP_DEFLATED) as archive:
    for path in sorted(dist.rglob("*")):
        if path.is_file():
            archive.write(path, Path("xinji-kwc-common") / path.relative_to(dist))
print(out)
