"""Run metadata and optimization-safe acceptance gates for derived data."""

import numpy as np

from mindtrace_ml.features import VERSION as FEATURES_VERSION
from mindtrace_ml.trajectory import CHANNELS
from mindtrace_ml.trajectory import VERSION as TRAJECTORY_VERSION


def run_metadata(window_ms, stride_ms, pressure):
    if window_ms <= 0 or stride_ms <= 0:
        raise ValueError("positive window duration and stride required")
    return dict(
        trajectory_version=TRAJECTORY_VERSION,
        features_version=FEATURES_VERSION,
        channels=list(CHANNELS),
        window_ms=window_ms,
        stride_ms=stride_ms,
        pressure=pressure,
        duplicate_policy="contiguous same-time same-state mean; transitions retained",
        reversed_time_policy="quarantine, never sort",
        short_window_policy="retain; no resampling or truncation",
        epoch_policy="missing; source provides relative milliseconds",
        normalization_fit="train only",
    )


def validate_features(features):
    if not np.isfinite(list(features["values"].values())).all():
        raise RuntimeError("feature acceptance failed: nonfinite statistic")


def validate_saved_window(saved, metadata):
    for name in saved:
        try:
            array = np.asarray(saved[name])
        except (ValueError, TypeError) as exc:
            raise RuntimeError("window acceptance failed: nonportable field") from exc
        if array.dtype.hasobject:
            raise RuntimeError("window acceptance failed: object array")
    values = saved["values"]
    if values.ndim != 2 or values.shape[1] != len(CHANNELS) or not np.isfinite(values).all():
        raise RuntimeError("window acceptance failed: invalid channel shape or nonfinite values")
    if str(saved["schema_version"]) != metadata["trajectory_version"]:
        raise RuntimeError("window acceptance failed: schema version mismatch")
    if str(saved["features_version"]) != metadata["features_version"]:
        raise RuntimeError("window acceptance failed: feature version mismatch")
    if (
        int(saved["window_ms"]) != metadata["window_ms"]
        or int(saved["stride_ms"]) != metadata["stride_ms"]
    ):
        raise RuntimeError("window acceptance failed: window policy mismatch")
