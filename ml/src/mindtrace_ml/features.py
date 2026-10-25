"""Dimensionless geometry and normalized-coordinate/second kinematics, v1."""

import numpy as np

VERSION = "statistics-v1.1-pauses-200-500-1000ms"


def extract(record):
    xy, p = record["normalized_xy"], record["raw_points"]
    speed = record["speed"][record["speed_valid"]]
    down = p[:, 4] == 1
    pressure = (p[down & record["feature_mask"][:, 3], 2] - record["pressure_offset"]) / record[
        "pressure_scale"
    ]
    dt = np.r_[0, np.diff(p[:, 3])] / 1000
    distance = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    valid_edge = down[1:] & down[:-1] & ~record["stroke_boundary"][1:]
    distance = distance[valid_edge]
    length = distance.sum()
    extent = np.ptp(xy, axis=0)
    duration = (p[-1, 3] - p[0, 3]) / 1000
    result, valid = {}, {}

    def put(name, value, available=True):
        result[name] = float(value) if available and np.isfinite(value) else 0.0
        valid[name] = bool(available and np.isfinite(value))

    put("duration_s", duration)
    put("point_count", len(p))
    put("down_fraction", down.mean())
    put("stroke_count", np.sum(down & record["stroke_boundary"]))
    put("path_length_normalized", length)
    put("width_normalized", extent[0])
    put("height_normalized", extent[1])
    put("bbox_area", extent.prod())
    put("aspect_ratio", extent[0] / max(extent[1], 1e-12), extent[1] > 0)
    # Sum each stroke chord, never connect separate strokes.
    starts = np.flatnonzero(record["stroke_boundary"])
    ends = np.r_[starts[1:], len(p)]
    chord = sum(
        np.linalg.norm(xy[e - 1] - xy[s]) for s, e in zip(starts, ends, strict=False) if down[s]
    )
    put("straightness", chord / max(length, 1e-12), length > 0)
    for name, array in [("speed", speed), ("pressure", pressure)]:
        for suffix, fn in [
            ("mean", np.mean),
            ("std", np.std),
            ("min", np.min),
            ("max", np.max),
            ("median", np.median),
        ]:
            put(f"{name}_{suffix}", fn(array) if len(array) else 0, len(array) > 0)
    # Consecutive valid speeds only; no acceleration across pen boundaries.
    idx = np.flatnonzero(record["speed_valid"])
    pairs = idx[1:][np.diff(idx) == 1]
    acceleration = (record["speed"][pairs] - record["speed"][pairs - 1]) / dt[pairs]
    put("acceleration_abs_mean", np.abs(acceleration).mean() if len(pairs) else 0, len(pairs) > 0)
    # Pause: maximal pen-up run duration, or a sampling gap of threshold duration.
    up_runs = [
        max(0, p[min(e, len(p) - 1), 3] - p[s, 3]) / 1000
        for s, e in zip(starts, ends, strict=False)
        if not down[s]
    ]
    for ms in (200, 500, 1000):
        put(
            f"pause_count_{ms}ms",
            sum(d >= ms / 1000 for d in up_runs)
            + np.sum((dt >= ms / 1000) & down & ~record["stroke_boundary"]),
        )
        put(
            f"pause_seconds_{ms}ms",
            sum(d for d in up_runs if d >= ms / 1000)
            + dt[(dt >= ms / 1000) & down & ~record["stroke_boundary"]].sum(),
        )
    put(
        "sampling_interval_median_ms",
        np.median(dt[dt > 0]) * 1000 if (dt > 0).any() else 0,
        (dt > 0).any(),
    )
    return dict(
        version=VERSION,
        values=result,
        feature_mask=valid,
        units="normalized coordinate units, seconds; not physical mm",
    )


def plot(record, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), layout="constrained")
    xy, t = record["normalized_xy"], record["relative_ms"] / 1000
    boundaries = np.flatnonzero(record["stroke_boundary"])
    for s, e in zip(boundaries, np.r_[boundaries[1:], len(xy)], strict=False):
        if record["raw_points"][s, 4] == 1:
            axes[0].plot(xy[s:e, 0], xy[s:e, 1], linewidth=0.6)
    axes[0].set(title="Normalized trajectory (pen-down strokes)", aspect="equal")
    axes[1].plot(t, np.where(record["speed_valid"], record["speed"], np.nan), linewidth=0.5)
    axes[1].set(ylabel="Normalized units / s")
    axes[2].plot(
        t, np.where(record["feature_mask"][:, 3], record["values"][:, 3], np.nan), linewidth=0.5
    )
    axes[2].set(
        xlabel="Relative seconds",
        ylabel=f"(Source pressure - {record['pressure_offset']:g}) / {record['pressure_scale']:g}",
    )
    fig.savefig(destination, dpi=130)
    plt.close(fig)
