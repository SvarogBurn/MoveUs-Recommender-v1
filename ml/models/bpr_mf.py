"""BPR matrix factorization (torch) with popularity fallback for unseen ids."""
import numpy as np
import torch

from ml.models.popularity import PopularityRec


class BPRMFRec:
    name = "BPR-MF"
    def __init__(self, dim=32, epochs=20, lr=0.05, seed=0):
        self.dim, self.epochs, self.lr, self.seed = dim, epochs, lr, seed
    def fit(self, ctx):
        self.fc = ctx.features
        self.fallback = PopularityRec(); self.fallback.fit(ctx)
        torch.manual_seed(self.seed); rng = np.random.default_rng(self.seed)
        uidx, eidx = self.fc.user_index, self.fc.event_index
        nU, nE = len(uidx), len(eidx)
        pos = [(uidx[int(r.user_id)], eidx[int(r.event_id)])
               for r in ctx.train.itertuples(index=False)
               if r.signal_type != "leave" and int(r.user_id) in uidx and int(r.event_id) in eidx]
        if not pos or nU == 0 or nE == 0:
            self.U = self.E = None; return
        pos = np.array(pos)
        self.U = torch.nn.Parameter(torch.randn(nU, self.dim) * 0.01)
        self.E = torch.nn.Parameter(torch.randn(nE, self.dim) * 0.01)
        opt = torch.optim.Adam([self.U, self.E], lr=self.lr)
        seen = {u: set() for u in range(nU)}
        for u, e in pos: seen[u].add(e)
        for _ in range(self.epochs):
            idx = rng.integers(0, len(pos), size=len(pos))
            u = pos[idx, 0]; i = pos[idx, 1]
            j = rng.integers(0, nE, size=len(pos))
            ut = torch.tensor(u); it = torch.tensor(i); jt = torch.tensor(j)
            opt.zero_grad()
            xui = (self.U[ut] * self.E[it]).sum(1)
            xuj = (self.U[ut] * self.E[jt]).sum(1)
            loss = -torch.log(torch.sigmoid(xui - xuj) + 1e-9).mean()
            loss.backward(); opt.step()
    def score(self, user_id, candidate_event_ids):
        cand = np.asarray(candidate_event_ids)
        if self.U is None or int(user_id) not in self.fc.user_index:
            return self.fallback.score(user_id, cand)
        u = self.fc.user_index[int(user_id)]
        out = np.zeros(len(cand))
        with torch.no_grad():
            uvec = self.U[u]
            for k, e in enumerate(cand):
                if int(e) in self.fc.event_index:
                    out[k] = float((uvec * self.E[self.fc.event_index[int(e)]]).sum())
                else:
                    out[k] = float(self.fallback.score(user_id, np.array([e]))[0])
        return out
