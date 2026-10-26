"""Portable checkpoint provenance and strict validation before state restoration."""

import hashlib
import json
import platform

import numpy as np
import torch

MODEL_CONFIG = dict(
    architecture="BiGRU",
    layers=2,
    hidden=64,
    bidirectional=True,
    dropout=0.2,
    representation=128,
    targets=4,
    inputs=16,
)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def environment():
    return dict(
        python=platform.python_version(),
        numpy=np.__version__,
        torch=str(torch.__version__),
        cuda=torch.version.cuda,
        cudnn=torch.backends.cudnn.version(),
    )


def sample_fingerprint(samples):
    digest = hashlib.sha256()
    for sample in samples:
        for key in ("values", "feature_mask", "stroke_boundary", "padding_mask", "source_spans"):
            if key in sample:
                a = np.ascontiguousarray(sample[key])
                digest.update(f"{key}:{a.dtype}:{a.shape}".encode())
                digest.update(a.tobytes())
        digest.update(json.dumps(sample.get("provenance", {}), sort_keys=True).encode())
    return digest.hexdigest()


def load_checked(path, expected):
    """Read on CPU; never restore model/optimizer/RNG until compatibility passes."""
    saved = torch.load(path, map_location="cpu", weights_only=True)
    actual = saved.get("contract")
    if (
        actual != expected
        or saved.get("contract_sha256") != fingerprint(expected)
        or not isinstance(saved.get("cursor"), int)
        or not 0 <= saved["cursor"] <= expected["training"]["updates"]
    ):
        raise ValueError("checkpoint input/configuration incompatible; original run preserved")
    return saved
