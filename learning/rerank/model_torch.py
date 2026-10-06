"""Neural reranker model (torch-optional; loaded lazily only when torch is present).

A small MLP scoring the per-candidate clinical feature row (the same 7 features the deterministic
scorer uses) to a scalar relevance score. Same output contract as the deterministic Reranker, so it
is a drop-in scorer. Importing this module does not import torch; torch is required lazily.
"""

from __future__ import annotations

from learning._torch import require_torch

# Per-candidate reranker feature dim (retrieval, embedding, supporting, objective, temporal, risk,
# contradictory). Kept in sync with Reranker._score / RerankerCheckpointMeta.
RERANK_INPUT_DIM = 7
RERANK_ARCH = "rerank_mlp.v1"
RERANK_FEATURE_VERSION = "rerank-feat.v1"


def build_reranker_mlp(input_dim: int = RERANK_INPUT_DIM, hidden: int = 32, dropout: float = 0.1):
    torch = require_torch()
    import torch.nn as nn

    class RerankScorer(nn.Module):
        def __init__(self, in_dim: int, h: int, p: float):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(p),
                nn.Linear(h, 1), nn.Sigmoid(),
            )

        def forward(self, x):
            return self.net(x).squeeze(-1)

    return RerankScorer(input_dim, hidden, dropout)
