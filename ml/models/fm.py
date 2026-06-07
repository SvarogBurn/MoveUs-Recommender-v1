"""Second-order factorization machine over dense pair features (torch)."""
import numpy as np
import torch
import torch.nn as nn

from ml.models._torch_pairs import build_pos_neg_pairs   # created in Task 6 step 3a


class _FM(nn.Module):
    def __init__(self, d, k=16):
        super().__init__()
        self.lin = nn.Linear(d, 1)
        self.V = nn.Parameter(torch.randn(d, k) * 0.01)
    def forward(self, x):
        linear = self.lin(x).squeeze(-1)
        xv = x @ self.V
        sq = (x ** 2) @ (self.V ** 2)
        inter = 0.5 * (xv ** 2 - sq).sum(1)
        return linear + inter


class FMRec:
    name = "FactorizationMachine"
    def __init__(self, k=16, epochs=15, lr=0.01, seed=0):
        self.k, self.epochs, self.lr, self.seed = k, epochs, lr, seed
    def fit(self, ctx):
        self.fc = ctx.features
        torch.manual_seed(self.seed)
        Xp, Xn = build_pos_neg_pairs(ctx, self.fc, seed=self.seed)
        d = Xp.shape[1]
        self.model = _FM(d, self.k)
        opt = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        bce = nn.BCEWithLogitsLoss()
        X = torch.tensor(np.vstack([Xp, Xn]), dtype=torch.float32)
        y = torch.tensor(np.concatenate([np.ones(len(Xp)), np.zeros(len(Xn))]), dtype=torch.float32)
        for _ in range(self.epochs):
            opt.zero_grad(); loss = bce(self.model(X), y); loss.backward(); opt.step()
    def score(self, user_id, candidate_event_ids):
        X = torch.tensor(self.fc.pair_dense(int(user_id), np.asarray(candidate_event_ids)),
                         dtype=torch.float32)
        with torch.no_grad():
            return self.model(X).numpy()
