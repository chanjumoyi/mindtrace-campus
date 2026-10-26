"""Plot private aggregate history; no participant data in the chart."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument("run", type=Path)
args = parser.parse_args()
history = json.loads((args.run / "history.json").read_text())
epochs = [row["epoch"] for row in history]
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].plot(epochs, [r["train_huber"] for r in history], label="Train (new masks)")
axes[0].plot(epochs, [r["validation"]["huber"] for r in history], label="Validation (fixed masks)")
axes[0].set(xlabel="Epoch", ylabel="Masked Huber (standardized)")
axes[0].legend()
axes[1].plot(epochs, [r["peak_allocated_bytes"] / 2**20 for r in history])
axes[1].set(xlabel="Epoch", ylabel="Peak allocated GPU memory (MiB)")
fig.tight_layout()
fig.savefig(args.run / "training-history.png", dpi=140)
