"""Deterministic seeding across python / numpy / torch (all optional).

Reproducibility matters for a clinical ML pipeline: the same snapshot + seed must produce the same
model. Seeds python's `random` always; numpy and torch only if installed (they are optional).
"""

from __future__ import annotations

import os
import random


def seed_everything(seed: int = 42) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        # Deterministic cudnn where available (best-effort; never fail if unsupported).
        try:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
        except Exception:
            pass
    except Exception:
        pass
