"""CPU/CUDA forward, backward, persistence and measured throughput; no dataset use."""

import json
import platform
import time
from pathlib import Path

import torch

torch.set_num_threads(4)
root = Path(__file__).resolve().parents[1]
(root / "checkpoints").mkdir(exist_ok=True)

result = dict(
    python=platform.python_version(),
    torch=torch.__version__,
    cuda_runtime=torch.version.cuda,
    cuda_available=torch.cuda.is_available(),
    cpu_threads=torch.get_num_threads(),
    devices={},
)
for device in ["cpu"] + (["cuda"] if torch.cuda.is_available() else []):
    torch.manual_seed(42)
    model = torch.nn.GRU(5, 64, num_layers=2, bidirectional=True, dropout=0.2, batch_first=True).to(
        device
    )
    x = torch.randn(32, 256, 5, device=device)
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    for _ in range(5):
        model.zero_grad(set_to_none=True)
        y, _ = model(x)
        y.square().mean().backward()
    if device == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    model.eval()
    with torch.no_grad():
        expected = model(x)[0]
    saved = root / "checkpoints" / f"environment-{device}.pt"
    torch.save(model.state_dict(), saved)
    restored = (
        torch.nn.GRU(5, 64, num_layers=2, bidirectional=True, dropout=0.2, batch_first=True)
        .to(device)
        .eval()
    )
    restored.load_state_dict(torch.load(saved, weights_only=True, map_location=device))
    with torch.no_grad():
        torch.testing.assert_close(expected, restored(x)[0])
    result["devices"][device] = dict(
        forward_backward=True,
        save_load_equal=True,
        windows_per_second=160 / elapsed,
        peak_allocated_bytes=torch.cuda.max_memory_allocated() if device == "cuda" else None,
    )
if torch.cuda.is_available():
    result["gpu"] = torch.cuda.get_device_name()
(root / "data/environment.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
if not torch.cuda.is_available():
    raise SystemExit("CUDA acceptance failed")
