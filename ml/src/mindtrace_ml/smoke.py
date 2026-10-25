"""Small real-data verification, including optimizer/RNG checkpoint continuation."""

import time

import torch
from torch.utils.data import DataLoader

from mindtrace_ml.model import BiGRU, collate, mask_batch, masked_huber


def execute(samples, validation, output, config, seed=42):
    if not samples or not validation:
        raise ValueError("smoke needs train and validation windows")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA acceptance required")
    torch.set_num_threads(4)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)
    device = "cuda"
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
        loss = masked_huber(prediction, batch)
        if not torch.isfinite(loss):
            raise RuntimeError("nonfinite smoke loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
        optimizer.step()
        return float(loss.detach())

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
                    model=model.state_dict(),
                    optimizer=optimizer.state_dict(),
                    cpu_rng=torch.get_rng_state(),
                    cuda_rng=torch.cuda.get_rng_state_all(),
                    mask_rng=generator.get_state(),
                    cursor=i + 1,
                    config=config,
                    seed=seed,
                    dropout_seed_policy="seed + update_index",
                ),
                checkpoint,
            )
            saved = torch.load(checkpoint, map_location=device, weights_only=True)
        if i == config["checkpoint_step"]:
            expected_loss = history[-1]
            expected_weights = {k: v.detach().clone() for k, v in model.state_dict().items()}
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    peak = torch.cuda.max_memory_allocated()
    expected_final_weights = {k: v.detach().clone() for k, v in model.state_dict().items()}
    # Cold model and optimizer; restore all randomness before the next update.
    model = BiGRU().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"])
    model.load_state_dict(saved["model"])
    optimizer.load_state_dict(saved["optimizer"])
    torch.set_rng_state(saved["cpu_rng"].cpu())
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
    losses = []
    validation_generator = torch.Generator().manual_seed(seed + 1)
    with torch.no_grad():
        for batch in DataLoader(
            validation, batch_size=config["batch_size"], collate_fn=collate, num_workers=0
        ):
            batch = {k: v.to(device) for k, v in mask_batch(batch, validation_generator).items()}
            prediction, _ = model(batch)
            losses.append(float(masked_huber(prediction, batch)))
    torch.save(
        dict(
            model=model.state_dict(),
            optimizer=optimizer.state_dict(),
            cursor=config["updates"],
            config=config,
            seed=seed,
            dropout_seed_policy="seed + update_index",
            cpu_rng=torch.get_rng_state(),
            cuda_rng=torch.cuda.get_rng_state_all(),
            mask_rng=generator.get_state(),
        ),
        output / "completed-smoke.pt",
    )
    return dict(
        status="passed",
        seed=seed,
        training_updates=config["updates"],
        train_windows=len(samples),
        validation_windows=len(validation),
        loss_history=history,
        validation_masked_huber=sum(losses) / len(losses),
        checkpoint_next_step_equal=True,
        checkpoint_completed_equal=True,
        dropout_seed_policy="seed + update_index",
        peak_allocated_bytes=peak,
        training_windows_per_second=sum(
            len(batches[i % len(batches)]["lengths"]) for i in range(config["updates"])
        )
        / elapsed,
        seconds=elapsed,
        gpu=torch.cuda.get_device_name(),
    )
