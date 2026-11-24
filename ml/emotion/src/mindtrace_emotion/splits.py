"""Participant-grouped split helpers.

Never split attempts randomly: the same participant can contribute several
attempts and sessions, and writer identity is an extremely strong shortcut.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Iterator


def unique_participants(values: Iterable[str]) -> list[str]:
    return sorted({str(value) for value in values if str(value).strip()})


def assign_participant_splits(
    participants: Iterable[str],
    *,
    seed: int = 42,
    train_fraction: float = 0.7,
    val_fraction: float = 0.15,
) -> dict[str, str]:
    """Deterministically assign whole participants to train/val/test."""
    values = unique_participants(participants)
    if not values:
        return {}
    if not (0.0 < train_fraction < 1.0):
        raise ValueError("train_fraction must be between 0 and 1")
    if not (0.0 <= val_fraction < 1.0 - train_fraction):
        raise ValueError("val_fraction is incompatible with train_fraction")
    random.Random(seed).shuffle(values)
    count = len(values)
    if count < 3:
        return {value: "train" for value in values}
    train_end = max(1, min(count - 2, round(count * train_fraction)))
    val_end = max(train_end + 1, min(count - 1, train_end + round(count * val_fraction)))
    result: dict[str, str] = {}
    for index, value in enumerate(values):
        if index < train_end:
            result[value] = "train"
        elif index < val_end:
            result[value] = "val"
        else:
            result[value] = "test"
    return result


def leave_one_participant_out(participants: Iterable[str]) -> Iterator[tuple[list[str], str]]:
    values = unique_participants(participants)
    for held_out in values:
        yield [value for value in values if value != held_out], held_out
