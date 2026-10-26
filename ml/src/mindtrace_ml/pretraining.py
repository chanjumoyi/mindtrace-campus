"""Formal masked reconstruction, epoch checkpoints and frozen evaluation."""

import json
import os
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from mindtrace_ml.checkpoint import MODEL_CONFIG, environment, fingerprint
from mindtrace_ml.data import sha256
from mindtrace_ml.model import BiGRU, collate, mask_batch, masked_huber, target_mask


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def save(path, value):
    temporary = path.with_suffix(".tmp")
    torch.save(value, temporary)
    os.replace(temporary, path)


def early_stop(history, patience, min_delta=0):
    best, best_epoch = float("inf"), 0
    for row in history:
        if row["validation"]["huber"] < best - min_delta:
            best, best_epoch = row["validation"]["huber"], row["epoch"]
    return best, best_epoch, bool(history and history[-1]["epoch"] - best_epoch >= patience)


def formal_contract(input_contract, config, device):
    return dict(
        input=input_contract,
        training=config,
        model=MODEL_CONFIG,
        environment=environment(),
        device=device,
    )


def complete_evaluation(output, history):
    """Validate frozen bindings, then repair derived files without another forward pass."""
    output = Path(output)
    claim = json.loads((output / "test-started.json").read_text())
    frozen = json.loads((output / "frozen.json").read_text())
    metrics = json.loads((output / "test-metrics.json").read_text())
    encoder_hash = sha256(output / "encoder.pt")
    if (
        claim["encoder_sha256"] != encoder_hash
        or metrics["encoder_sha256"] != encoder_hash
        or claim["frozen_sha256"] != sha256(output / "frozen.json")
        or metrics["evaluation_count"] != 1
    ):
        raise ValueError("frozen encoder/test binding incompatible; existing files preserved")
    summary = dict(
        **frozen,
        test=metrics["metrics"],
        test_windows=metrics["windows"],
        encoder_sha256=encoder_hash,
        total_training_seconds=sum(row["seconds"] for row in history),
        completed=True,
    )
    summary_path = output / "summary.json"
    previous = json.loads(summary_path.read_text()) if summary_path.exists() else None
    if previous and previous.get("completed") and previous != summary:
        raise ValueError("completed summary incompatible; existing files preserved")
    history_path = output / "history.json"
    if not history_path.exists() or json.loads(history_path.read_text()) != history:
        write_json(history_path, history)
    if previous != summary:
        write_json(summary_path, summary)
    return summary


def resume_completed(output, config, input_contract, device="cuda"):
    """Handle test-stage recovery before model construction or frozen file writes."""
    output = Path(output)
    claim = output / "test-started.json"
    metrics = output / "test-metrics.json"
    summary = output / "summary.json"
    completed = summary.exists() and json.loads(summary.read_text()).get("completed")
    if not (claim.exists() or metrics.exists() or completed):
        return False
    if not claim.exists() or not metrics.exists():
        raise RuntimeError(
            "test evaluation previously started; review interruption before a new evaluation"
        )
    expected = formal_contract(input_contract, config, device)
    saved = torch.load(output / "last.pt", map_location="cpu", weights_only=True)
    frozen = json.loads((output / "frozen.json").read_text())
    if (
        saved["contract"] != expected
        or saved["contract_sha256"] != fingerprint(expected)
        or frozen["contract_sha256"] != fingerprint(expected)
    ):
        raise ValueError("incompatible formal checkpoint; existing files preserved")
    history = saved["history"]
    best, best_epoch, stopped = early_stop(history, config["patience"], config["min_delta"])
    if (
        not history
        or len(history) != frozen["epochs"]
        or [row["epoch"] for row in history] != list(range(1, len(history) + 1))
        or len(history) > config["max_epochs"]
        or not (len(history) == config["max_epochs"] or stopped)
        or frozen["best_epoch"] != best_epoch
        or frozen["validation_huber"] != best
        or frozen["early_stopped"] != stopped
        or frozen["test_used_for_selection"] is not False
    ):
        raise ValueError("incomplete or incompatible frozen history; existing files preserved")
    complete_evaluation(output, history)
    return True


def evaluate(model, samples, config, device, seed):
    """Fixed masks; globally target-weighted metrics, also per reconstruction channel."""
    model.eval()
    generator = torch.Generator().manual_seed(seed)
    count = torch.zeros(4, dtype=torch.float64, device=device)
    sums = torch.zeros(3, 4, dtype=torch.float64, device=device)
    with torch.no_grad():
        for batch in DataLoader(samples, batch_size=config["batch_size"], collate_fn=collate):
            batch = {
                k: v.to(device)
                for k, v in mask_batch(batch, generator, config["mask_fraction"]).items()
            }
            prediction, _ = model(batch)
            valid = target_mask(batch)
            # Select before arithmetic, so absent targets cannot poison metrics.
            for channel in range(4):
                error = (
                    prediction[..., channel][valid[..., channel]]
                    - batch["target"][..., channel][valid[..., channel]]
                )
                count[channel] += error.numel()
                absolute = error.abs().double()
                sums[0, channel] += torch.where(
                    absolute < 1, absolute.square() / 2, absolute - 0.5
                ).sum()
                sums[1, channel] += absolute.sum()
                sums[2, channel] += absolute.square().sum()
    if not count.sum() or not torch.isfinite(sums).all():
        raise ValueError("no valid evaluation targets or nonfinite metrics")
    counts, totals = count.cpu(), sums.cpu()
    return dict(
        huber=float(totals[0].sum() / counts.sum()),
        targets=int(counts.sum()),
        mae=float(totals[1].sum() / counts.sum()),
        rmse=float((totals[2].sum() / counts.sum()).sqrt()),
        channels={
            name: dict(
                targets=int(counts[i]),
                huber=float(totals[0, i] / counts[i]) if counts[i] else None,
                mae=float(totals[1, i] / counts[i]) if counts[i] else None,
                rmse=float((totals[2, i] / counts[i]).sqrt()) if counts[i] else None,
            )
            for i, name in enumerate(("dx", "dy", "dt_seconds", "pressure"))
        },
    )


def train(training, validation, output, config, input_contract, device="cuda", resume=False):
    output = Path(output)
    if (output / "test-started.json").exists() or (output / "test-metrics.json").exists():
        raise RuntimeError("test evaluation already started; use completion recovery")
    if not training or not validation:
        raise ValueError("nonempty official train and validation required")
    if not 0 < config["mask_fraction"] < 1 or config["max_epochs"] < 1 or config["patience"] < 1:
        raise ValueError("invalid training schedule")
    torch.set_num_threads(4)
    torch.manual_seed(config["seed"])
    torch.cuda.manual_seed_all(config["seed"])
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)
    contract = formal_contract(input_contract, config, device)
    model = BiGRU().to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config["learning_rate"], weight_decay=config["weight_decay"]
    )
    history, update = [], 0
    if resume:
        saved = torch.load(output / "last.pt", map_location="cpu", weights_only=True)
        if saved["contract"] != contract or saved["contract_sha256"] != fingerprint(contract):
            raise ValueError("incompatible formal checkpoint")
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        history, update = saved["history"], saved["updates"]
        torch.set_rng_state(saved["cpu_rng"])
        if device == "cuda":
            torch.cuda.set_rng_state_all(saved["cuda_rng"])
    elif (output / "last.pt").exists():
        raise ValueError("existing training requires explicit resume")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "contract.json", contract)
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    _, _, stopped = early_stop(history, config["patience"], config["min_delta"])
    for epoch in range(len(history) + 1, config["max_epochs"] + 1):
        if stopped:
            break
        started = time.perf_counter()
        generator = torch.Generator().manual_seed(config["seed"] + epoch)
        loader = DataLoader(
            training,
            batch_size=config["batch_size"],
            shuffle=True,
            generator=torch.Generator().manual_seed(config["seed"] + epoch),
            collate_fn=collate,
        )
        model.train()
        total, targets, skipped = 0.0, 0, 0
        optimizer.zero_grad(set_to_none=True)
        accumulation = config["gradient_accumulation"]
        # Accumulate SUM losses and divide gradients by actual measured targets.
        group_targets = 0
        for index, batch in enumerate(loader):
            torch.manual_seed(config["seed"] + update)
            torch.cuda.manual_seed_all(config["seed"] + update)
            batch = {
                k: v.to(device)
                for k, v in mask_batch(batch, generator, config["mask_fraction"]).items()
            }
            count = int(target_mask(batch).sum())
            if count:
                prediction, _ = model(batch)
                loss = masked_huber(prediction, batch)
                if not torch.isfinite(loss):
                    raise RuntimeError("nonfinite training loss")
                (loss * count).backward()
                total += float(loss.detach()) * count
                targets += count
                group_targets += count
            else:
                skipped += 1
            if (index + 1) % accumulation == 0 or index + 1 == len(loader):
                if group_targets:
                    for parameter in model.parameters():
                        if parameter.grad is not None:
                            parameter.grad.div_(group_targets)
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(), config["gradient_clip"], error_if_nonfinite=True
                    )
                    optimizer.step()
                    update += 1
                optimizer.zero_grad(set_to_none=True)
                group_targets = 0
        if not targets:
            raise ValueError("epoch has no measured masked targets")
        metrics = evaluate(model, validation, config, device, config["validation_seed"])
        if device == "cuda":
            torch.cuda.synchronize()
        row = dict(
            epoch=epoch,
            train_huber=total / targets,
            train_targets=targets,
            skipped_batches=skipped,
            validation=metrics,
            seconds=time.perf_counter() - started,
            peak_allocated_bytes=torch.cuda.max_memory_allocated() if device == "cuda" else 0,
        )
        history.append(row)
        _, best_epoch, stopped = early_stop(history, config["patience"], config["min_delta"])
        state = dict(
            contract=contract,
            contract_sha256=fingerprint(contract),
            model=model.state_dict(),
            optimizer=optimizer.state_dict(),
            history=history,
            updates=update,
            cpu_rng=torch.get_rng_state(),
            cuda_rng=torch.cuda.get_rng_state_all() if device == "cuda" else [],
            dropout_seed_policy="seed + optimizer update index; epoch-derived shuffle/masking",
        )
        if best_epoch == epoch:
            save(output / "best.pt", state)
        save(output / "last.pt", state)
        write_json(output / "history.json", history)
        print(
            json.dumps(
                dict(
                    epoch=epoch,
                    train=row["train_huber"],
                    validation=metrics["huber"],
                    best_epoch=best_epoch,
                    seconds=row["seconds"],
                )
            ),
            flush=True,
        )
    # last.pt is authoritative if interruption happened before history.json.
    # This also runs when a terminal checkpoint leaves no epochs to execute.
    write_json(output / "history.json", history)
    best, best_epoch, stopped = early_stop(history, config["patience"], config["min_delta"])
    saved = torch.load(output / "best.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(saved["model"])
    save(
        output / "encoder.pt",
        dict(
            encoder=model.encoder.state_dict(),
            contract=contract,
            best_epoch=best_epoch,
            validation_huber=best,
        ),
    )
    write_json(
        output / "frozen.json",
        dict(
            status="frozen",
            best_epoch=best_epoch,
            validation_huber=best,
            epochs=len(history),
            early_stopped=stopped,
            contract_sha256=fingerprint(contract),
            test_used_for_selection=False,
        ),
    )
    return model, history
