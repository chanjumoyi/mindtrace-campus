"""Plot aggregate diagnostics from a completed private window study."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    result = json.loads((args.run / "summary.json").read_text())
    if result["status"] != "passed":
        raise ValueError("only completed studies may be plotted")
    candidates = json.loads((args.run / "comparison.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), layout="constrained")
    for name, smoke in result["smoke"].items():
        axes[0].plot(
            range(1, len(smoke["loss_history"]) + 1), smoke["loss_history"], marker="o", label=name
        )
    axes[0].set(
        xlabel="Training update",
        ylabel="Masked Huber",
        title="Finite-loss smoke diagnostics (not model ranking)",
    )
    axes[0].legend()
    axes[1].barh([c["id"] for c in candidates], [c["coverage"] for c in candidates])
    axes[1].axvline(0.99, linestyle="--", color="red", label="Required coverage")
    axes[1].set(
        xlim=(0, 1.01),
        xlabel="Worst writer mean record coverage",
        title="Validation pen-down time coverage",
    )
    axes[1].legend()
    fig.savefig(args.run / "diagnostics.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
