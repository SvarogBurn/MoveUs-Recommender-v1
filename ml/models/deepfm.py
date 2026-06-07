"""DeepFM: FM second-order term + deep MLP over dense pair features (torch)."""
import numpy as np
import torch
import torch.nn as nn

from ml.models._torch_pairs import build_pos_neg_pairs


class _DeepFM(nn.Module):
    def __init__(self, d, k=16, hidden=(64, 32)):
        super().__init__()
        self.lin = nn.Linear(d, 1)
        self.V = nn.Parameter(torch.randn(d, k) * 0.01)
        layers, prev = [], d
        for h in hidden:
            layers += [nn.Linear(prev, h), nn.ReLU()]; prev = h
        layers += [nn.Linear(prev, 1)]
        self.mlp = nn.Sequential(*layers)
    def forward(self, x):
        linear = self.lin(x).squeeze(-1)
        xv = x @ self.V; sq = (x ** 2) @ (self.V ** 2)
        inter = 0.5 * (xv ** 2 - sq).sum(1)
        deep = self.mlp(x).squeeze(-1)
        return linear + inter + deep


class DeepFMRec:
    name = "DeepFM"
    def __init__(self, k=16, epochs=15, lr=0.01, seed=0):
        self.k, self.epochs, self.lr, self.seed = k, epochs, lr, seed
    def fit(self, ctx):
        self.fc = ctx.features
        torch.manual_seed(self.seed)
        self.dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        Xp, Xn = build_pos_neg_pairs(ctx, self.fc, seed=self.seed)
        d = Xp.shape[1]
        self.model = _DeepFM(d, self.k).to(self.dev)
        opt = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        bce = nn.BCEWithLogitsLoss()
        X = torch.tensor(np.vstack([Xp, Xn]), dtype=torch.float32).to(self.dev)
        y = torch.tensor(np.concatenate([np.ones(len(Xp)), np.zeros(len(Xn))]), dtype=torch.float32).to(self.dev)
        for _ in range(self.epochs):
            opt.zero_grad(); loss = bce(self.model(X), y); loss.backward(); opt.step()
    def score(self, user_id, candidate_event_ids):
        X = torch.tensor(self.fc.pair_dense(int(user_id), np.asarray(candidate_event_ids)),
                         dtype=torch.float32).to(self.dev)
        with torch.no_grad():
            return self.model(X).cpu().numpy()
