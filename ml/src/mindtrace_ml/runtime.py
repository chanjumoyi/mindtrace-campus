"""Explicit per-process resource settings; never change system CPU configuration."""

import os


def cpu_affinity(mask=None):
    if mask is None:
        return None
    if mask <= 0:
        raise ValueError("CPU affinity mask must be positive")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        handle = kernel.GetCurrentProcess()
        if not kernel.SetProcessAffinityMask(handle, mask):
            raise ctypes.WinError(ctypes.get_last_error())
        process_mask, system_mask = ctypes.c_size_t(), ctypes.c_size_t()
        kernel.GetProcessAffinityMask.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.POINTER(ctypes.c_size_t),
        ]
        if not kernel.GetProcessAffinityMask(
            handle, ctypes.byref(process_mask), ctypes.byref(system_mask)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        if process_mask.value != mask:
            raise RuntimeError("CPU affinity readback differs from requested mask")
    else:
        cpus = {i for i in range(mask.bit_length()) if mask & (1 << i)}
        os.sched_setaffinity(0, cpus)
        if os.sched_getaffinity(0) != cpus:
            raise RuntimeError("CPU affinity readback differs from requested mask")
    return hex(mask)
