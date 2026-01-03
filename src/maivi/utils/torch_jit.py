"""Utilities to keep TorchScript optional in packaged builds."""

from __future__ import annotations

import os


def disable_torch_jit() -> None:
    """Disable TorchScript to avoid source inspection failures in bundles."""
    os.environ.setdefault("TORCH_JIT", "0")

    try:
        import torch
    except Exception:
        return

    try:
        if hasattr(torch, "_C") and hasattr(torch._C, "_jit_set_enabled"):
            torch._C._jit_set_enabled(False)
    except Exception:
        # Best-effort only; failure to disable should not crash the app.
        return
