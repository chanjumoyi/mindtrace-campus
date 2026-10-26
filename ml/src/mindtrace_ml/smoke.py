"""Small real-data verification, including optimizer/RNG checkpoint continuation."""

import json
import time

import torch
from torch.utils.data import DataLoader

from mindtrace_ml.checkpoint import (
    MODEL_CONFIG,
    environment,
    fingerprint,
    load_checked,
    sample_fingerprint,
)
from mindtrace_ml.model import BiGRU, collate, mask_batch, masked_huber, target_mask


def execute(samples, validation, output, config, seed=42, *, input_contract, device="cuda"):
    if not samples or not validation:
        raise ValueError("smoke needs train and validation windows")
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA acceptance required")
    torch.set_num_threads(4)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)
    if not 0 < config["checkpoint_step"] < config["updates"]:
        raise ValueError("checkpoint must precede the final update")
    contract = dict(
        input=input_contract,
        training=config,
        seed=seed,
        model=MODEL_CONFIG,
        environment=environment(),
        device=device,
        train_windows_sha256=sample_fingerprint(samples),
        validation_windows_sha256=sample_fingerprint(validation),
    )
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        samples, batch_size=config["batch_size"], shuffle=False, collate_fn=collate, num_workers=0
    )
    batches = list(loader)
    model = BiGRU().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"])

    def step(index):
        # cuDNN RNN dropout has an internal state not represented in state_dict.
        # Derive its seed from the saved update cursor, rather than relying on
        # restoring only the public CUDA RNG state after cold construction.
        torch.manual_seed(seed + index)
        torch.cuda.manual_seed_all(seed + index)
        model.train()
        batch = mask_batch(batches[index % len(batches)], generator, config["mask_fraction"])
        batch = {k: v.to(device) for k, v in batch.items()}
        optimizer.zero_grad(set_to_none=True)
        prediction, _ = model(batch)
        if not target_mask(batch).any():
            raise ValueError("training batch has no measured masked targets")
        loss = masked_huber(prediction, batch)
        if not torch.isfinite(loss):
            raise RuntimeError("nonfinite smoke loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
        optimizer.step()
        return float(loss.detach())

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
    started = time.perf_counter()
    history = []
    checkpoint = output / "checkpoint.pt"
    output.mkdir(parents=True, exist_ok=False)
    saved = None
    for i in range(config["updates"]):
        history.append(step(i))
        if i + 1 == config["checkpoint_step"]:
            torch.save(
                dict(
                    contract=contract,
                    contract_sha256=fingerprint(contract),
                    loss_history=history.copy(),
                    model=model.state_dict(),
                    optimizer=optimizer.state_dict(),
                    cpu_rng=torch.get_rng_state(),
                    cuda_rng=torch.cuda.get_rng_state_all() if device == "cuda" else [],
                    mask_rng=generator.get_state(),
                    cursor=i + 1,
                    config=config,
                    seed=seed,
                    dropout_seed_policy="seed + update_index",
                ),
                checkpoint,
            )
            saved = load_checked(checkpoint, contract)
        if i == config["checkpoint_step"]:
            expected_loss = history[-1]
            expected_weights = {k: v.detach().clone() for k, v in model.state_dict().items()}
    if device == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    peak = torch.cuda.max_memory_allocated() if device == "cuda" else 0
    expected_final_weights = {k: v.detach().clone() for k, v in model.state_dict().items()}
    # Cold model and optimizer; restore all randomness before the next update.
    model = BiGRU().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"])
    model.load_state_dict(saved["model"])
    optimizer.load_state_dict(saved["optimizer"])
    torch.set_rng_state(saved["cpu_rng"].cpu())
    if device == "cuda":
        torch.cuda.set_rng_state_all([state.cpu() for state in saved["cuda_rng"]])
    generator.set_state(saved["mask_rng"].cpu())
    resumed_loss = step(saved["cursor"])
    torch.testing.assert_close(
        torch.tensor(expected_loss), torch.tensor(resumed_loss), rtol=1e-5, atol=1e-7
    )
    for name, value in model.state_dict().items():
        torch.testing.assert_close(value, expected_weights[name], rtol=1e-5, atol=1e-7)
    # Complete the same update count after the verified continuation.
    for i in range(saved["cursor"] + 1, config["updates"]):
        step(i)
    for name, value in model.state_dict().items():
        torch.testing.assert_close(value, expected_final_weights[name], rtol=1e-5, atol=1e-7)
    model.eval()
    loss_sum, target_count = 0.0, 0
    validation_generator = torch.Generator().manual_seed(seed + 1)
    with torch.no_grad():
        for batch in DataLoader(
            validation, batch_size=config["batch_size"], collate_fn=collate, num_workers=0
        ):
            batch = {
                k: v.to(device)
                for k, v in mask_batch(batch, validation_generator, config["mask_fraction"]).items()
            }
            prediction, _ = model(batch)
            count = int(target_mask(batch).sum())
            loss_sum += float(masked_huber(prediction, batch)) * count
            target_count += count
    if not target_count:
        raise ValueError("validation has no measured masked targets")
    torch.save(
        dict(
            contract=contract,
            contract_sha256=fingerprint(contract),
            loss_history=history,
            validation_masked_huber=loss_sum / target_count,
            model=model.state_dict(),
            optimizer=optimizer.state_dict(),
            cursor=config["updates"],
            config=config,
            seed=seed,
            dropout_seed_policy="seed + update_index",
            cpu_rng=torch.get_rng_state(),
            cuda_rng=torch.cuda.get_rng_state_all() if device == "cuda" else [],
            mask_rng=generator.get_state(),
        ),
        output / "completed-smoke.pt",
    )
    # This smoke evaluates once; its sole evaluated checkpoint is its best smoke checkpoint.
    # Formal multi-epoch early stopping remains a separate task.
    import shutil

    shutil.copy2(output / "completed-smoke.pt", output / "best-smoke.pt")
    (output / "history.json").write_text(
        json.dumps(
            dict(
                training=history,
                validation_masked_huber=loss_sum / target_count,
                validation_targets=target_count,
            ),
            indent=2,
        )
    )
    return dict(
        status="passed",
        seed=seed,
        training_updates=config["updates"],
        train_windows=len(samples),
        validation_windows=len(validation),
        loss_history=history,
        validation_masked_huber=loss_sum / target_count,
        validation_targets=target_count,
        contract_sha256=fingerprint(contract),
        checkpoint_next_step_equal=True,
        checkpoint_completed_equal=True,
        dropout_seed_policy="seed + update_index",
        peak_allocated_bytes=peak,
        training_windows_per_second=sum(
            len(batches[i % len(batches)]["lengths"]) for i in range(config["updates"])
        )
        / elapsed,
        seconds=elapsed,
        gpu=torch.cuda.get_device_name() if device == "cuda" else "CPU synthetic test",
    )
