"""Read-only canonical EMOTHAW quality audit. Does not run exploratory or formal analysis."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mindtrace_ml.data import ML_ROOT, config, sha256, source_root
from mindtrace_ml.emothaw import audit
from mindtrace_ml.emothaw_permissions import readiness
from mindtrace_ml.pretraining import write_json
from mindtrace_ml.runtime import cpu_affinity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--formal-readiness", action="store_true")
    parser.add_argument("--cpu-affinity", type=lambda value: int(value, 0))
    args = parser.parse_args()
    affinity = cpu_affinity(args.cpu_affinity)
    workbook = source_root("emothaw") / "extracted/DataEmothaw/DASS_scores.xls"
    gate = readiness(args.evidence, workbook)
    gate["formal_training_reminder"] = "还未展开正式训练"
    if args.formal_readiness:
        print(json.dumps(gate, indent=2))
        return 0 if gate["status"] == "ready_for_preregistration" else 2
    output = (
        ML_ROOT
        / "experiments/emothaw-adaptation"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    output.mkdir(parents=True, exist_ok=False)
    result = audit()
    summary = result["summary"]
    summary["formal_training_status"] = gate["status"]
    summary["formal_training_reminder"] = "还未展开正式训练"
    summary["blockers"] = gate["reasons"]
    result["readiness"] = gate
    result["source_settings"] = config()["emothaw"]
    result["cpu_affinity"] = affinity
    result["code_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ML_ROOT, text=True
    ).strip()
    result["implementation_sha256"] = {
        str(p.relative_to(ML_ROOT)): sha256(p)
        for p in [
            Path(__file__),
            ML_ROOT / "src/mindtrace_ml/emothaw.py",
            ML_ROOT / "src/mindtrace_ml/emothaw_permissions.py",
        ]
    }
    write_json(output / "private-audit.json", result)
    write_json(output / "summary.json", summary)
    write_json(
        output / "experiment-status.json",
        dict(
            stage="B",
            reminder="还未展开正式训练；取得书面授权、核实镜像计分和来源单位、完成已有探索复核及方案预登记后再开展训练。",
            status="skipped_pending_evidence" if gate["reasons"] else "awaiting_preregistration",
            experiments={
                name: dict(status="not_executed", reasons=gate["reasons"])
                for name in ("EXP-02", "EXP-03", "EXP-04", "EXP-05")
            },
            allowed_fallback="OUHD-L -> MindTrace",
            future_protocol=dict(
                outer_participant_folds=5,
                inner_participant_folds=3,
                seeds=[42, 43, 44],
                targets=["depression", "anxiety", "stress"],
                baseline_models=["Dummy", "Ridge", "RandomForest"],
                encoder_modes=["scratch", "frozen_ouhd", "partial_finetune"],
                common_splits_and_budget=True,
                fit_preprocessing="inner_training_participants_only",
                task_aggregation="one participant per outcome; task/win rows not independent participants",
                metrics=["MAE", "RMSE", "Spearman"],
                classification_enabled=False,
                status="proposed_not_registered_or_executed",
            ),
        ),
    )
    print(json.dumps(dict(output=str(output), **summary), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
