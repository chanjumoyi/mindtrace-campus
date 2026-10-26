"""Private file inventory of all configured download roots; does not move data."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mindtrace_ml.data import ML_ROOT, config, sha256, source_root

output = ML_ROOT / "data/inventory"
output.mkdir(parents=True, exist_ok=True)
summary = {}
for name, settings in config().items():
    if settings["root"] is None:
        summary[name] = dict(status="not_available")
        continue
    root = source_root(name)
    if name == "emothaw":
        root = root.parent  # Inventory all downloads; adapter still has one canonical root.
    files = [
        dict(path=p.relative_to(root).as_posix(), bytes=p.stat().st_size, sha256=sha256(p))
        for p in root.rglob("*")
        if p.is_file()
    ]
    (output / f"{name}.json").write_text(json.dumps(dict(settings=settings, files=files), indent=2))
    summary[name] = dict(
        files=len(files), bytes=sum(f["bytes"] for f in files), permission=settings["permission"]
    )
(output / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
