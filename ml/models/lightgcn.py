"""LightGCN (torch) over the train user-event bipartite graph; popularity fallback."""
import numpy as np
import torch

from ml.models.popularity import PopularityRec


class LightGCNRec:
    name = "LightGCN"
    def __init__(self, dim=32, layers=2, epochs=20, lr=0.05, seed=0):
        self.dim, self.layers, self.epochs, self.lr, self.seed = dim, layers, epochs, lr, seed
    def fit(self, ctx):
        self.fc = ctx.features
        self.U = None  # guard for score(): only set to a Parameter in the degenerate branch
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
        n = nU + nE
        # symmetric-normalized adjacency of the bipartite graph
        rows = np.concatenate([pos[:, 0], nU + pos[:, 1]])
        cols = np.concatenate([nU + pos[:, 1], pos[:, 0]])
        deg = np.bincount(rows, minlength=n).astype(float)
        dinv = 1.0 / np.sqrt(np.maximum(deg, 1.0))
        vals = dinv[rows] * dinv[cols]
        A = torch.sparse_coo_tensor(np.vstack([rows, cols]), torch.tensor(vals, dtype=torch.float32),
                                    (n, n)).coalesce()
        emb = torch.nn.Parameter(torch.randn(n, self.dim) * 0.01)
        opt = torch.optim.Adam([emb], lr=self.lr)

        def propagate(e):
            outs = [e]; x = e
            for _ in range(self.layers):
                x = torch.sparse.mm(A, x); outs.append(x)
            return torch.stack(outs).mean(0)

        for _ in range(self.epochs):
            allemb = propagate(emb)
            idx = rng.integers(0, len(pos), size=len(pos))
            u = torch.tensor(pos[idx, 0]); i = torch.tensor(nU + pos[idx, 1])
            j = torch.tensor(nU + rng.integers(0, nE, size=len(pos)))
            opt.zero_grad()
            xui = (allemb[u] * allemb[i]).sum(1)
            xuj = (allemb[u] * allemb[j]).sum(1)
            loss = -torch.log(torch.sigmoid(xui - xuj) + 1e-9).mean()
            loss.backward(); opt.step()
        with torch.no_grad():
            self.final = propagate(emb)
        self.nU = nU
    def score(self, user_id, candidate_event_ids):
        cand = np.asarray(candidate_event_ids)
        if self.U is None and not hasattr(self, "final"):
            return self.fallback.score(user_id, cand)
        if int(user_id) not in self.fc.user_index:
            return self.fallback.score(user_id, cand)
        u = self.fc.user_index[int(user_id)]
        out = np.zeros(len(cand))
        with torch.no_grad():
            uvec = self.final[u]
            for k, e in enumerate(cand):
                if int(e) in self.fc.event_index:
                    out[k] = float((uvec * self.final[self.nU + self.fc.event_index[int(e)]]).sum())
                else:
                    out[k] = float(self.fallback.score(user_id, np.array([e]))[0])
        return out
