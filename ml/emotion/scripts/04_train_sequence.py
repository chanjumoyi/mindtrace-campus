#!/usr/bin/env python3
"""Participant-grouped BiGRU classifier for handwriting emotion labels.

The encoder is the same 16-channel BiGRU used by the OUHD-L masked
reconstruction experiment, so an existing ``encoder.pt`` can initialise it.
Start with ``03_train_baseline.py``; only move here after the feature baseline
shows signal and you have enough labeled participants.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ml/src"))

from mindtrace_emotion.labels import TAXONOMY_VERSION, normalize_emotion
from mindtrace_emotion.sequence import build_sequence

from mindtrace_ml.model import BiGRU, collate

ROOT = Path(__file__).resolve().parents[3]

try:
    from sklearn.metrics import accuracy_score, f1_score, recall_score
except ImportError as error:  # pragma: no cover
    raise SystemExit("scikit-learn is required: install ml/emotion/requirements.txt") from error


class EmotionBiGRU(nn.Module):
    def __init__(self, num_classes: int, pretrained_encoder: Path | None = None) -> None:
        super().__init__()
        self.encoder = BiGRU().encoder
        if pretrained_encoder is not None:
            state = torch.load(pretrained_encoder, map_location="cpu")
            encoder_state = state.get("encoder", state) if isinstance(state, dict) else state
            missing, unexpected = self.encoder.load_state_dict(encoder_state, strict=False)
            if missing or unexpected:
                print(
                    "warning: pretrained encoder keys differ; "
                    f"missing={len(missing)} unexpected={len(unexpected)}",
                    flush=True,
                )
        self.dropout = nn.Dropout(0.2)
        self.head = nn.Linear(128, num_classes)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
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
        return self.head(self.dropout(pooled))


@lru_cache(maxsize=16)
def _load_payload(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class AttemptDataset(Dataset):
    def __init__(
        self,
        rows: pd.DataFrame,
        data_root: Path,
        max_len: int,
        class_to_index: dict[str, int],
    ) -> None:
        self.rows = rows.reset_index(drop=True)
        self.data_root = data_root
        self.max_len = max_len
        self.class_to_index = class_to_index

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict:
        row = self.rows.iloc[index]
        path = Path(str(row["source_path"]))
        if not path.is_absolute():
            path = self.data_root / path
        payload = _load_payload(str(path.resolve()))
        attempt_id = str(row["attempt_id"])
        attempt = next(
            (
                item
                for item in payload.get("attempts", [])
                if str(item.get("attemptId")) == attempt_id
            ),
            None,
        )
        if attempt is None:
            raise ValueError(f"attempt {attempt_id} not found in {path}")
        sequence = build_sequence(attempt.get("points", []), attempt.get("canvas"), self.max_len)
        return {
            "values": torch.as_tensor(sequence["values"], dtype=torch.float32),
            "feature_mask": torch.as_tensor(sequence["feature_mask"], dtype=torch.bool),
            "stroke_boundary": torch.as_tensor(sequence["stroke_boundary"], dtype=torch.bool),
            "label": torch.tensor(self.class_to_index[str(row["emotion"])], dtype=torch.long),
        }


def collate_with_labels(samples: list[dict]) -> dict:
    labels = torch.stack([sample.pop("label") for sample in samples])
    batch = collate(samples)
    batch["label"] = labels
    return batch


def group_folds(participants: list[str], n_splits: int, seed: int):
    unique = sorted(set(participants))
    random.Random(seed).shuffle(unique)
    folds: list[list[str]] = [[] for _ in range(min(n_splits, len(unique)))]
    for index, participant in enumerate(unique):
        folds[index % len(folds)].append(participant)
    for fold in folds:
        held_out = set(fold)
        yield [participant for participant in unique if participant not in held_out], fold


def metrics(truth: list[int], predicted: list[int], classes: list[str]) -> dict:
    labels = list(range(len(classes)))
    return {
        "accuracy": float(accuracy_score(truth, predicted)),
        "macro_f1": float(
            f1_score(truth, predicted, labels=labels, average="macro", zero_division=0)
        ),
        "per_class_recall": {
            name: float(value)
            for name, value in zip(
                classes,
                recall_score(
                    truth, predicted, labels=labels, average=None, zero_division=0
                ).tolist(),
                strict=True,
            )
        },
    }


def evaluate(
    model: nn.Module, loader: DataLoader, device: torch.device
) -> tuple[list[int], list[int]]:
    model.eval()
    truth: list[int] = []
    predicted: list[int] = []
    with torch.no_grad():
        for batch in loader:
            labels = batch.pop("label")
            batch = {key: value.to(device) for key, value in batch.items()}
            logits = model(batch)
            truth.extend(labels.tolist())
            predicted.extend(logits.argmax(dim=1).cpu().tolist())
    return truth, predicted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--data-root", type=Path, required=True, help="root used when building source_path"
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--pretrained-encoder", type=Path)
    parser.add_argument("--cv", choices=("loso", "group5"), default="group5")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--max-len", type=int, default=512)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--freeze-encoder-epochs", type=int, default=0)
    parser.add_argument("--include-weak", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    output = args.output_dir or (
        ROOT / "ml/emotion/runs" / f"sequence-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    )
    output.mkdir(parents=True, exist_ok=False)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device(args.device)

    frame = pd.read_csv(args.manifest, encoding="utf-8-sig")
    frame["emotion"] = frame["emotion"].fillna("").map(normalize_emotion)
    frame["label_source"] = frame["label_source"].fillna("").astype(str)
    if not args.include_weak:
        frame = frame[frame["label_source"].isin(["", "manual"])]
    frame = frame[frame["emotion"].notna()].copy()
    frame["participant_id"] = frame["participant_id"].astype(str)
    classes = sorted(frame["emotion"].unique().tolist())
    if len(classes) < 2:
        raise SystemExit("fewer than two emotion classes with labels; nothing to train")
    class_to_index = {name: index for index, name in enumerate(classes)}
    frame["label_index"] = frame["emotion"].map(class_to_index).astype(int)

    participant_folds = (
        [
            (list(set(frame["participant_id"]) - {participant}), [participant])
            for participant in sorted(set(frame["participant_id"]))
        ]
        if args.cv == "loso"
        else list(group_folds(frame["participant_id"].tolist(), 5, args.seed))
    )
    fold_results: list[dict] = []
    prediction_rows: list[dict] = []
    for fold_index, (train_participants, test_participants) in enumerate(participant_folds, 1):
        train = frame[frame["participant_id"].isin(train_participants)]
        test = frame[frame["participant_id"].isin(test_participants)]
        if train.empty or test.empty or train["emotion"].nunique() < 2:
            continue
        train_dataset = AttemptDataset(train, args.data_root, args.max_len, class_to_index)
        test_dataset = AttemptDataset(test, args.data_root, args.max_len, class_to_index)
        train_loader = DataLoader(
            train_dataset,
            batch_size=args.batch_size,
            shuffle=True,
            collate_fn=collate_with_labels,
        )
        test_loader = DataLoader(
            test_dataset,
            batch_size=args.batch_size,
            shuffle=False,
            collate_fn=collate_with_labels,
        )
        model = EmotionBiGRU(len(classes), args.pretrained_encoder).to(device)
        if args.freeze_encoder_epochs:
            for parameter in model.encoder.parameters():
                parameter.requires_grad = False
        counts = torch.bincount(
            torch.as_tensor(train["label_index"].to_numpy()), minlength=len(classes)
        ).float()
        weights = torch.where(
            counts > 0, counts.sum() / (len(classes) * counts), torch.zeros_like(counts)
        )
        criterion = nn.CrossEntropyLoss(weight=weights.to(device), label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
        best_f1 = -math.inf
        best_epoch = 0
        best_state = None
        history: list[dict] = []
        for epoch in range(1, args.epochs + 1):
            if args.freeze_encoder_epochs and epoch == args.freeze_encoder_epochs + 1:
                for parameter in model.encoder.parameters():
                    parameter.requires_grad = True
            model.train()
            total_loss = 0.0
            for batch in train_loader:
                labels = batch.pop("label").to(device)
                batch = {key: value.to(device) for key, value in batch.items()}
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(model(batch), labels)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += float(loss.detach())
            truth, predicted = evaluate(model, test_loader, device)
            score = metrics(truth, predicted, classes)["macro_f1"]
            history.append(
                {
                    "epoch": epoch,
                    "train_loss": total_loss / max(1, len(train_loader)),
                    "val_macro_f1": score,
                }
            )
            if score > best_f1:
                best_f1 = score
                best_epoch = epoch
                best_state = {
                    key: value.detach().cpu().clone() for key, value in model.state_dict().items()
                }
            elif epoch - best_epoch >= args.patience:
                break
        if best_state is not None:
            model.load_state_dict(best_state)
        truth, predicted = evaluate(model, test_loader, device)
        result = metrics(truth, predicted, classes)
        result.update(
            {
                "fold": fold_index,
                "best_epoch": best_epoch,
                "history": history,
                "train_participants": sorted(train_participants),
                "test_participants": sorted(test_participants),
            }
        )
        fold_results.append(result)
        for row, predicted_index in zip(test.itertuples(), predicted, strict=True):
            prediction_rows.append(
                {
                    "fold": fold_index,
                    "session_id": row.session_id,
                    "participant_id": row.participant_id,
                    "attempt_id": row.attempt_id,
                    "emotion": row.emotion,
                    "predicted": classes[int(predicted_index)],
                }
            )
        torch.save(
            {
                "model": best_state,
                "classes": classes,
                "fold": fold_index,
                "config": vars(args),
                "history": history,
            },
            output / f"fold-{fold_index}.pt",
        )
        print(
            json.dumps(
                {"fold": fold_index, "best_epoch": best_epoch, "macro_f1": best_f1},
                ensure_ascii=False,
            )
        )

    if not fold_results:
        raise SystemExit("no fold had both training and test labels")
    pooled_truth = [class_to_index[row["emotion"]] for row in prediction_rows]
    pooled_predicted = [class_to_index[row["predicted"]] for row in prediction_rows]
    pooled = metrics(pooled_truth, pooled_predicted, classes)
    summary = {
        "taxonomy_version": TAXONOMY_VERSION,
        "classes": classes,
        "cv": args.cv,
        "pretrained_encoder": str(args.pretrained_encoder) if args.pretrained_encoder else None,
        "participants": int(frame["participant_id"].nunique()),
        "labeled_attempts": len(frame),
        "pooled": pooled,
        "folds": fold_results,
        "macro_f1_mean": float(np.mean([row["macro_f1"] for row in fold_results])),
        "macro_f1_std": float(np.std([row["macro_f1"] for row in fold_results])),
    }
    (output / "metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    pd.DataFrame(prediction_rows).to_csv(
        output / "predictions.csv", index=False, encoding="utf-8-sig"
    )
    card = f"""# Handwriting emotion BiGRU

- Taxonomy: `{TAXONOMY_VERSION}` ({", ".join(classes)})
- CV: {args.cv}; pretrained encoder: {args.pretrained_encoder or "none"}
- Labeled attempts: {len(frame)}; participants: {frame["participant_id"].nunique()}
- Pooled macro-F1: {pooled["macro_f1"]:.3f}
- Fold macro-F1: {summary["macro_f1_mean"]:.3f} ± {summary["macro_f1_std"]:.3f}

This is exploratory research on handwriting behaviour, not a diagnostic
instrument.  Report participant-grouped results only; random attempt splits
leak writer identity.
"""
    (output / "model-card.md").write_text(card, encoding="utf-8")
    print(
        json.dumps(
            {
                "pooled": pooled,
                "macro_f1_mean": summary["macro_f1_mean"],
                "macro_f1_std": summary["macro_f1_std"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"run: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
