"""Versioned normalization, duplicate repair and provenance-preserving windows."""

import numpy as np

from mindtrace_ml.data import config

VERSION = "ouhd-trajectory-v1.1"
CHANNELS = ("dx", "dy", "dt_seconds", "pressure", "pen_state")


def pressure_parameters(pressure_range=None):
    """Default range comes only from the source config; other devices inject theirs."""
    bounds = np.asarray(
        config()["ouhd_l"]["pressure_range"] if pressure_range is None else pressure_range,
        dtype=float,
    )
    if bounds.shape != (2,) or not np.isfinite(bounds).all() or bounds[1] <= bounds[0]:
        raise ValueError("pressure range must have two finite increasing bounds")
    return dict(range=bounds.tolist(), offset=float(bounds[0]), scale=float(bounds[1] - bounds[0]))


def browser_pressure_mask(pressure, pointer_types, pen_down):
    """MindTrace dynamic pressure rule, separate from OUHD source scaling."""
    pressure = np.asarray(pressure, dtype=float)
    pointer_types, pen_down = np.asarray(pointer_types), np.asarray(pen_down, dtype=bool)
    if not (pressure.shape == pointer_types.shape == pen_down.shape):
        raise ValueError("pressure metadata shape mismatch")
    valid = (
        np.isfinite(pressure)
        & (pressure >= 0)
        & (pressure <= 1)
        & (pointer_types == "pen")
        & pen_down
    )
    values = pressure[valid]
    if len(values) < 2 or np.ptp(values) < 0.01 - 1e-12:
        return np.zeros_like(valid)
    return valid


class Quarantine(ValueError):
    pass


def repair(points):
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] != 5 or not len(p):
        raise Quarantine("invalid shape")
    if not np.isfinite(p[:, [0, 1, 3, 4]]).all():
        raise Quarantine("nonfinite position/time/state")
    if np.isinf(p[:, 2]).any() or not np.isin(p[:, 4], [0, 1]).all():
        raise Quarantine("invalid pressure/state")
    if (np.diff(p[:, 3]) < 0).any():
        raise Quarantine("reversed time; do not sort")
    if not (np.diff(p[:, 3]) == 0).any():
        indices = np.arange(len(p))
        return (
            p.copy(),
            np.column_stack([indices, indices + 1]),
            dict(merged_points=0, zero_dt_transitions=0),
        )
    groups = np.r_[0, np.flatnonzero((np.diff(p[:, 3]) != 0) | (np.diff(p[:, 4]) != 0)) + 1, len(p)]
    starts, ends = groups[:-1], groups[1:]
    out = p[starts].copy()
    out[:, :2] = np.add.reduceat(p[:, :2], starts, axis=0) / (ends - starts)[:, None]
    valid = np.isfinite(p[:, 2])
    pressure_count = np.add.reduceat(valid.astype(int), starts)
    pressure_sum = np.add.reduceat(np.where(valid, p[:, 2], 0), starts)
    out[:, 2] = np.divide(
        pressure_sum, pressure_count, out=np.full(len(starts), np.nan), where=pressure_count > 0
    )
    return (
        out,
        np.column_stack([starts, ends]),
        dict(
            merged_points=len(p) - len(out),
            zero_dt_transitions=int((np.diff(out[:, 3]) == 0).sum()),
        ),
    )


def fit_coordinates(training_points):
    low = np.full(2, np.inf)
    high = np.full(2, -np.inf)
    count = 0
    for split, points in training_points:
        if split != "train":
            raise ValueError("coordinate fit accepts training split only")
        low = np.minimum(low, points[:, :2].min(axis=0))
        high = np.maximum(high, points[:, :2].max(axis=0))
        count += 1
    if not count:
        raise ValueError("empty training set")
    return dict(
        origin=low.tolist(),
        scale=np.maximum(high - low, 1).tolist(),
        fit_split="train",
        method="training_coordinate_extent",
        physical_calibration=False,
    )


def transform(points, coordinate_map, pressure_range=None):
    pressure = pressure_parameters(pressure_range)
    p, spans, quality = repair(points)
    xy = (p[:, :2] - coordinate_map["origin"]) / coordinate_map["scale"]
    dt = np.r_[0, np.diff(p[:, 3])] / 1000
    boundary = np.r_[True, np.diff(p[:, 4]) != 0]
    delta = np.vstack([np.zeros(2), np.diff(xy, axis=0)])
    values = np.column_stack(
        [delta, dt, (np.nan_to_num(p[:, 2]) - pressure["offset"]) / pressure["scale"], p[:, 4]]
    )
    mask = np.ones_like(values, dtype=bool)
    mask[0, :3] = False
    mask[:, 3] = (
        np.isfinite(p[:, 2]) & (p[:, 2] >= pressure["range"][0]) & (p[:, 2] <= pressure["range"][1])
    )
    values[~mask] = 0
    speed_valid = (dt > 0) & ~boundary & (p[:, 4] == 1)
    speed = np.divide(np.linalg.norm(delta, axis=1), dt, out=np.zeros(len(p)), where=speed_valid)
    return dict(
        values=values,
        feature_mask=mask,
        measurement_missing=~mask,
        augmentation_mask=np.zeros_like(mask),
        padding_mask=np.zeros(len(p), bool),
        stroke_boundary=boundary,
        raw_points=p,
        normalized_xy=xy,
        relative_ms=p[:, 3] - p[0, 3],
        source_time_ms=p[:, 3],
        epoch_ms=np.full(len(p), np.nan),
        epoch_available=False,
        source_spans=spans,
        speed=speed,
        speed_valid=speed_valid,
        quality=quality,
        version=VERSION,
        pressure_range=tuple(pressure["range"]),
        pressure_offset=pressure["offset"],
        pressure_scale=pressure["scale"],
    )


class Standardizer:
    def fit(self, records):
        total, square, count = np.zeros(4), np.zeros(4), np.zeros(4)
        for split, record in records:
            if split != "train":
                raise ValueError("standardization requires training split")
            x, mask = record["values"][:, :4], record["feature_mask"][:, :4]
            total += np.where(mask, x, 0).sum(axis=0)
            square += np.where(mask, x * x, 0).sum(axis=0)
            count += mask.sum(axis=0)
        if not count.all():
            raise ValueError("channel without training observations")
        self.mean = total / count
        self.scale = np.sqrt(np.maximum(square / count - self.mean**2, 1e-12))
        return self

    def apply(self, values, mask):
        result = values.copy()
        result[:, :4] = (result[:, :4] - self.mean) / self.scale
        return np.where(mask, result, 0)

    def inverse(self, values):
        result = values.copy()
        result[:, :4] = result[:, :4] * self.scale + self.mean
        return result


def windows(record, duration_ms=2000, stride_ms=2000):
    if duration_ms <= 0 or stride_ms <= 0:
        raise ValueError("positive window duration and stride required")
    t = record["relative_ms"]
    for start in np.arange(0, t[-1] + 1, stride_ms):
        indices = np.flatnonzero((t >= start) & (t < start + duration_ms))
        if not len(indices):
            continue
        result = {
            k: v[indices].copy()
            if isinstance(v, np.ndarray) and v.ndim > 0 and len(v) == len(t)
            else v
            for k, v in record.items()
        }
        # Retain source deltas and mark first delta invalid: it refers outside window.
        result["feature_mask"][0, :3] = False
        result["measurement_missing"][0, :3] = True
        result["values"][0, :3] = 0
        result["speed_valid"][0] = False
        result["stroke_boundary"][0] = True
        result["source_indices"] = indices
        result["time_bounds_ms"] = (float(start), float(start + duration_ms))
        yield result


def pad(window, length):
    """Pad every point array to length, preserving metadata and the input window.

    Model values use zero, validity/missing/augmentation flags use false, index
    arrays use -1, auxiliary floating measurements use NaN. Only padding_mask
    is true on padding. Scalar metadata and the pressure/time-bound metadata
    vectors stay unchanged, including their ndarray form after NPZ loading.
    """
    n = len(window["values"])
    if length < n:
        raise ValueError("padding must not truncate")
    result = dict(window)
    for name, array in window.items():
        if not isinstance(array, np.ndarray):
            continue
        if array.ndim == 0 or name in ("pressure_range", "time_bounds_ms"):
            result[name] = array.copy()
            continue
        if len(array) != n:
            raise ValueError(f"point array length mismatch: {name}")
        if name == "values" or np.issubdtype(array.dtype, np.bool_):
            fill = 0
        elif np.issubdtype(array.dtype, np.integer):
            fill = -1
        elif np.issubdtype(array.dtype, np.floating):
            fill = np.nan
        else:
            raise ValueError(f"unsupported point array type: {name}")
        result[name] = np.pad(
            array, [(0, length - n)] + [(0, 0)] * (array.ndim - 1), constant_values=fill
        )
    result["padding_mask"][n:] = True
    return result
