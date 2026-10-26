"""Event-preserving time windows with auditable resampling; no split fitting."""

import numpy as np

from mindtrace_ml.trajectory import transform, windows

VERSION = "event-windows-v3"


def prepare(points, coordinates, rate_hz=None, max_gap_ms=200, pressure_range=None):
    source = transform(points, coordinates, pressure_range)
    if not np.isfinite(max_gap_ms) or max_gap_ms <= 0:
        raise ValueError("maximum gap must be positive")
    p = source["raw_points"]
    breaks = np.r_[True, (np.diff(p[:, 4]) != 0) | (np.diff(p[:, 3]) > max_gap_ms)]
    segments = np.cumsum(breaks) - 1
    if rate_hz is None:
        result = source
        left = right = np.arange(len(p))
        alpha = np.zeros(len(p))
        target_segments = segments
    else:
        if not np.isfinite(rate_hz) or rate_hz <= 0:
            raise ValueError("rate must be positive")
        rows, lefts, rights, alphas, ids = [], [], [], [], []
        starts = np.flatnonzero(breaks)
        for segment, (start, end) in enumerate(
            zip(starts, np.r_[starts[1:], len(p)], strict=False)
        ):
            group = p[start:end]
            t = group[:, 3]
            if group[0, 4] == 1 and len(t) > 1:
                target = np.unique(np.r_[t[0], np.arange(t[0], t[-1], 1000 / rate_hz), t[-1]])
            else:
                target = np.unique([t[0], t[-1]])
            r = np.searchsorted(t, target, side="left").clip(0, len(t) - 1)
            lo = np.maximum(r - 1, 0)
            lo[t[r] == target] = r[t[r] == target]
            weight = np.divide(
                target - t[lo], t[r] - t[lo], out=np.zeros(len(target)), where=t[r] > t[lo]
            )
            interpolated = group[lo] * (1 - weight[:, None]) + group[r] * weight[:, None]
            # Do not synthesize pressure from an absent or invalid endpoint.
            pressure_valid = (
                source["feature_mask"][start + lo, 3] & source["feature_mask"][start + r, 3]
            )
            interpolated[~pressure_valid, 2] = np.nan
            interpolated[:, 3] = target
            interpolated[:, 4] = group[0, 4]
            rows.append(interpolated)
            lefts.append(start + lo)
            rights.append(start + r)
            alphas.append(weight)
            ids.append(np.full(len(target), segment))
        result = transform(np.concatenate(rows), coordinates, source["pressure_range"])
        left, right, alpha = np.concatenate(lefts), np.concatenate(rights), np.concatenate(alphas)
        target_segments = np.concatenate(ids)
    boundary = np.r_[True, np.diff(target_segments) != 0]
    result["stroke_boundary"] = boundary
    result["feature_mask"][boundary, :2] = False
    result["values"][boundary, :2] = 0
    result["measurement_missing"] = ~result["feature_mask"]
    result["speed_valid"][boundary] = False
    result["speed"][boundary] = 0
    result["segment_ids"] = target_segments
    result["source_left_spans"] = source["source_spans"][left]
    result["source_right_spans"] = source["source_spans"][right]
    result["source_alpha"] = alpha
    result["source_spans"] = np.column_stack(
        [source["source_spans"][left, 0], source["source_spans"][right, 1]]
    )
    result["version"] = VERSION
    return result


def time_windows(
    record,
    duration_ms=2000,
    stride_ms=2000,
    short_minimum_ms=500,
    minimum_down_points=2,
    max_gap_ms=200,
):
    if not 0 < short_minimum_ms <= duration_ms:
        raise ValueError("invalid short window policy")
    end = record["relative_ms"][-1]
    # Sampling interval is included at the final point, but never extends over a gap.
    positive = np.diff(record["relative_ms"])
    positive = positive[(positive > 0) & (positive <= max_gap_ms)]
    tolerance = float(np.median(positive)) if len(positive) else 0
    for window in windows(record, duration_ms, stride_ms):
        start, _ = window["time_bounds_ms"]
        if end - start + tolerance < short_minimum_ms:
            continue
        if np.sum(window["raw_points"][:, 4] == 1) < minimum_down_points:
            continue
        window["relative_ms"] = window["relative_ms"] - start
        window["version"] = VERSION
        yield window


def point_windows(record, size=256):
    """Debug only: fixed point counts must never be a formal cross-domain policy."""
    if size <= 0:
        raise ValueError("point window size must be positive")
    n = len(record["values"])
    for start in range(0, n, size):
        stop = min(start + size, n)
        result = {
            k: v[start:stop].copy()
            if isinstance(v, np.ndarray) and v.ndim and len(v) == n
            else v.copy()
            if isinstance(v, np.ndarray)
            else v
            for k, v in record.items()
        }
        if np.sum(result["raw_points"][:, 4] == 1) < 2:
            continue
        result["values"][0, :3] = 0
        result["feature_mask"][0, :3] = False
        result["measurement_missing"][0, :3] = True
        result["stroke_boundary"][0] = True
        result["source_indices"] = np.arange(start, stop)
        result["time_bounds_ms"] = (
            float(record["relative_ms"][start]),
            float(record["relative_ms"][stop - 1]),
        )
        result["version"] = "debug-256-only"
        yield result


def preservation(source, sampled):
    """Error on original pen-down observations, never interpolating across segments."""
    for key in ("pressure_range", "pressure_offset", "pressure_scale"):
        if not np.array_equal(source[key], sampled[key]):
            raise ValueError("incompatible pressure contract")
    errors, pressure_errors = [], []
    pressure_total = 0
    for segment in np.unique(source["segment_ids"]):
        a = np.flatnonzero((source["segment_ids"] == segment) & (source["raw_points"][:, 4] == 1))
        b = np.flatnonzero(sampled["segment_ids"] == segment)
        if not len(a) or not len(b):
            continue
        t, target = sampled["source_time_ms"][b], source["source_time_ms"][a]
        reconstructed = np.column_stack(
            [np.interp(target, t, sampled["normalized_xy"][b, c]) for c in range(2)]
        )
        errors.extend(np.linalg.norm(reconstructed - source["normalized_xy"][a], axis=1))
        pressure_total += int(source["feature_mask"][a, 3].sum())
        right = np.searchsorted(t, target).clip(0, len(t) - 1)
        left = np.maximum(right - 1, 0)
        left[t[right] == target] = right[t[right] == target]
        valid = (
            source["feature_mask"][a, 3]
            & sampled["feature_mask"][b[left], 3]
            & sampled["feature_mask"][b[right], 3]
        )
        reconstructed_pressure = np.interp(target, t, sampled["values"][b, 3])
        pressure_errors.extend(
            np.abs(reconstructed_pressure[valid] - source["values"][a[valid], 3])
        )
    return dict(
        position_p95=float(np.quantile(errors, 0.95)) if errors else None,
        pressure_p95=float(np.quantile(pressure_errors, 0.95)) if pressure_errors else None,
        pressure_comparable_fraction=len(pressure_errors) / pressure_total
        if pressure_total
        else 0.0,
    )
