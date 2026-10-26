"""Packed BiGRU with separate observation, augmentation and padding semantics."""

import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

INPUT_CHANNELS = (
    [f"value/{c}" for c in ("dx", "dy", "dt_seconds", "pressure", "pen_state")]
    + [f"valid/{i}" for i in range(5)]
    + [f"masked/{i}" for i in range(5)]
    + ["stroke_boundary"]
)


class BiGRU(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.GRU(
            len(INPUT_CHANNELS), 64, num_layers=2, bidirectional=True, dropout=0.2, batch_first=True
        )
        self.head = nn.Linear(128, 4)

    def forward(self, batch):
        x = torch.cat(
            [
                batch["observed"],
                batch["feature_mask"].float(),
                batch["augmentation_mask"].float(),
                batch["stroke_boundary"].float().unsqueeze(-1),
            ],
            dim=-1,
        )
        packed = pack_padded_sequence(
            x, batch["lengths"].cpu(), batch_first=True, enforce_sorted=False
        )
        sequence, _ = self.encoder(packed)
        sequence, _ = pad_packed_sequence(sequence, batch_first=True, total_length=x.shape[1])
        valid = ~batch["padding_mask"]
        pooled = (sequence * valid.unsqueeze(-1)).sum(dim=1) / valid.sum(dim=1, keepdim=True)
        reconstruction = self.head(sequence).masked_fill(~valid.unsqueeze(-1), 0)
        return reconstruction, pooled


def collate(samples):
    if not samples or any(len(s["values"]) == 0 for s in samples):
        raise ValueError("empty batch/window")
    lengths = []
    for sample in samples:
        v = torch.as_tensor(sample["values"])
        m = torch.as_tensor(sample["feature_mask"], dtype=torch.bool)
        pad = torch.as_tensor(sample.get("padding_mask", torch.zeros(len(v))), dtype=torch.bool)
        if v.shape != (len(v), 5) or m.shape != v.shape or pad.shape != (len(v),):
            raise ValueError("invalid sample shape")
        length = int((~pad).sum())
        if length == 0 or pad[:length].any() or not pad[length:].all():
            raise ValueError("padding must be a nonempty prefix followed by padding")
        if not torch.isfinite(v[:length][m[:length]]).all():
            raise ValueError("nonfinite valid measurement")
        lengths.append(length)
    lengths = torch.tensor(lengths)
    n, width = len(samples), int(lengths.max())
    values = torch.zeros(n, width, 5)
    mask = torch.zeros(n, width, 5, dtype=torch.bool)
    boundary = torch.zeros(n, width, dtype=torch.bool)
    padding = torch.arange(width).unsqueeze(0) >= lengths.unsqueeze(1)
    for i, sample in enumerate(samples):
        length = lengths[i]
        values[i, :length] = torch.as_tensor(sample["values"][:length], dtype=torch.float32)
        mask[i, :length] = torch.as_tensor(sample["feature_mask"][:length], dtype=torch.bool)
        values[i, :length].masked_fill_(~mask[i, :length], 0)
        boundary[i, :length] = torch.as_tensor(sample["stroke_boundary"][:length], dtype=torch.bool)
    return dict(
        target=values,
        observed=values.clone(),
        feature_mask=mask,
        augmentation_mask=torch.zeros_like(mask),
        padding_mask=padding,
        measurement_missing=~mask & ~padding.unsqueeze(-1),
        stroke_boundary=boundary,
        lengths=lengths,
    )


def mask_batch(batch, generator, fraction=0.15):
    result = {k: v.clone() for k, v in batch.items()}
    for i, length in enumerate(batch["lengths"].tolist()):
        boundaries = torch.nonzero(batch["stroke_boundary"][i, :length]).flatten().tolist()
        boundaries = sorted(set([0, *boundaries, length]))
        needed = max(1, round(length * fraction))
        available = [
            (a, b)
            for a, b in zip(boundaries[:-1], boundaries[1:], strict=False)
            if batch["feature_mask"][i, a:b, :4].any()
        ]
        if not available:
            continue
        for index in torch.randperm(len(available), generator=generator).tolist():
            a, b = available[index]
            count = min(needed, b - a)
            offset = int(torch.randint(b - a - count + 1, (1,), generator=generator))
            result["augmentation_mask"][i, a + offset : a + offset + count, :4] = batch[
                "feature_mask"
            ][i, a + offset : a + offset + count, :4]
            needed -= count
            if needed <= 0:
                break
    result["observed"][result["augmentation_mask"]] = 0
    return result


def target_mask(batch):
    return (
        batch["augmentation_mask"][..., :4]
        & batch["feature_mask"][..., :4]
        & ~batch["padding_mask"].unsqueeze(-1)
    )


def masked_huber(prediction, batch):
    valid = target_mask(batch)
    selected = prediction.masked_select(valid)
    if not selected.numel():
        return selected.sum()
    return torch.nn.functional.huber_loss(
        selected, batch["target"][..., :4].masked_select(valid), reduction="mean"
    )
