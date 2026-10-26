"""Read-only source adapters. No labels, demographics or paths in public summaries."""

import csv
import hashlib
import json
from array import array
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[2]


def config():
    return json.loads((ML_ROOT / "configs/data.json").read_text(encoding="utf-8"))


def source_root(name):
    value = config()[name]["root"]
    if value is None:
        raise ValueError(f"{name}: not_available")
    return (ML_ROOT / value).resolve()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(root=None):
    root = Path(root or source_root("ouhd_l")).resolve()
    records, owners, paths = [], {}, set()
    for split in ("train", "val", "test"):
        with (root / f"{split}.csv").open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                writer = row["writer_id"].strip()
                if not writer:
                    raise ValueError("missing writer_id")
                if writer in owners and owners[writer] != split:
                    raise ValueError("writer crosses official splits")
                owners[writer] = split
                path = (root / row["csv"]).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError("missing or escaping trajectory path")
                if path in paths:
                    raise ValueError("duplicate manifest path")
                paths.add(path)
                records.append(
                    dict(
                        path=path,
                        writer_id=writer,
                        split=split,
                        source_id=path.relative_to(root).as_posix(),
                    )
                )
    return records


def read_points(path):
    import numpy as np

    # Read only original measurements, never supplied derivative columns.
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream))
    positions = (0, 1, 2, 7, 22)
    if len(header) <= 22 or tuple(header[i] for i in positions) != (
        "X cood.",
        "Y cood.",
        "Pressure",
        "Time",
        "pen_down",
    ):
        raise ValueError("OUHD-L measurement schema mismatch")

    def measurement(value):
        return float(value) if value.strip() else float("nan")

    # Source trajectory rows are strictly numeric and unquoted. Stream into a
    # flat numeric buffer: native CSV/loadtxt and nested row allocations proved
    # unstable during large-file scans on this Windows runtime.
    buffer = array("d")
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        next(stream)
        try:
            for line in stream:
                if not line.strip():
                    continue  # Blank separators contain no measurement.
                row = line.rstrip("\r\n").split(",")
                if len(row) != len(header):
                    raise ValueError("trajectory row width differs from header")
                buffer.extend(
                    (
                        measurement(row[0]),
                        measurement(row[1]),
                        measurement(row[2]),
                        measurement(row[7]),
                        measurement(row[22]),
                    )
                )
        except (IndexError, TypeError) as exc:
            raise ValueError("malformed OUHD-L measurement row") from exc
    values = np.frombuffer(buffer, dtype=np.float64).reshape(-1, 5).copy()
    return values  # x, y, pressure, relative time milliseconds, pen state
