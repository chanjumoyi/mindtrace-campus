"""Participant isolation and synthetic regression plumbing; no real experiment runner."""

from collections import defaultdict

import numpy as np
import torch
from torch import nn

from mindtrace_ml.checkpoint import MODEL_CONFIG
from mindtrace_ml.model import BiGRU


def group_folds(keys, folds=5, seed=42):
    participants = sorted(set(keys))
    if type(folds) is not int or folds < 2 or len(participants) < folds:
        raise ValueError("insufficient independent participants for folds")
    permutation = np.random.default_rng(seed).permutation(len(participants))
    buckets = np.array_split(permutation, folds)
    for bucket in buckets:
        held = {participants[int(i)] for i in bucket}
        yield dict(train=[p for p in participants if p not in held], test=sorted(held))


def nested_folds(keys, outer=5, inner=3, seed=42):
    result = []
    for fold in group_folds(keys, outer, seed):
        within = list(group_folds(fold["train"], inner, seed))
        if any(set(fold["test"]) & (set(f["train"]) | set(f["test"])) for f in within):
            raise RuntimeError("participant leakage")
        result.append(dict(**fold, inner=within))
    return result


def aggregate_windows(rows, expected_tasks=tuple(range(1, 8))):
    """Window -> task mean -> participant mean, never treating windows as people."""
    if not rows:
        raise ValueError("empty participant data")
    tasks = defaultdict(list)
    sessions = defaultdict(set)
    for row in rows:
        sessions[row["participant"]].add(row.get("session", 1))
        if len(sessions[row["participant"]]) > 1:
            raise ValueError("multiple sessions require review")
        value = np.asarray(row["features"], dtype=float)
        if value.ndim != 1 or not len(value) or not np.isfinite(value).all():
            raise ValueError("invalid feature vector")
        tasks[(row["participant"], row["task"])].append(value)
    people = defaultdict(dict)
    for (person, task), values in tasks.items():
        people[person][task] = np.mean(np.stack(values), axis=0)
    result = {}
    for person, values in people.items():
        if set(values) != set(expected_tasks):
            raise ValueError("missing or unexpected task; review before aggregation")
        result[person] = np.mean(np.stack([values[t] for t in expected_tasks]), axis=0)
    return result


class RegressionPipeline(nn.Module):
    """Three continuous outputs; classification is deliberately absent."""

    def __init__(self, mode, pretrained=None):
        super().__init__()
        if mode not in ("scratch", "frozen_ouhd", "partial_finetune"):
            raise ValueError("unsupported encoder mode")
        if mode != "scratch" and pretrained is None:
            raise ValueError("transfer requires explicit pretrained encoder")
        if mode == "scratch" and pretrained is not None:
            raise ValueError("scratch must not load pretrained weights")
        self.backbone = BiGRU()
        if pretrained is not None:
            if pretrained["contract"]["model"] != MODEL_CONFIG:
                raise ValueError("incompatible pretrained architecture")
            self.backbone.encoder.load_state_dict(pretrained["encoder"], strict=True)
        self.mode = mode
        self.heads = nn.ModuleList([nn.Linear(128, 1) for _ in range(3)])
        for parameter in self.backbone.head.parameters():
            parameter.requires_grad_(False)
        for name, parameter in self.backbone.encoder.named_parameters():
            parameter.requires_grad_(
                mode == "scratch" or (mode == "partial_finetune" and "_l1" in name)
            )

    def forward(self, batch):
        if self.mode == "frozen_ouhd":
            self.backbone.eval()
        _, representation = self.backbone(batch)
        return torch.cat([head(representation) for head in self.heads], dim=-1)
