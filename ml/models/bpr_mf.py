"""BPR matrix factorization (torch) over the user x activity matrix.

Events never recur, so item embeddings are keyed on the event's *activity*
(a recurring node) rather than its unique id; a brand-new event is scored via the
embedding of its activity. Unseen users fall back to the popularity baseline."""
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
        self.event_activity = {int(e): int(a) for e, a in
                               zip(ctx.events["event_id"], ctx.events["activity_id"])}
        acts = sorted(set(self.event_activity.values()))
        self.act_index = {a: i for i, a in enumerate(acts)}

        torch.manual_seed(self.seed); rng = np.random.default_rng(self.seed)
        uidx = self.fc.user_index
        nU, nA = len(uidx), len(self.act_index)
        pos = [(uidx[int(r.user_id)], self.act_index[self.event_activity[int(r.event_id)]])
               for r in ctx.train.itertuples(index=False)
               if r.signal_type != "leave" and int(r.user_id) in uidx
               and int(r.event_id) in self.event_activity]
        if not pos or nU == 0 or nA == 0:
            self.U = self.E = None; return
        pos = np.array(pos)
        self.U = torch.nn.Parameter(torch.randn(nU, self.dim) * 0.01)
        self.E = torch.nn.Parameter(torch.randn(nA, self.dim) * 0.01)
        opt = torch.optim.Adam([self.U, self.E], lr=self.lr)
        for _ in range(self.epochs):
            idx = rng.integers(0, len(pos), size=len(pos))
            u = pos[idx, 0]; i = pos[idx, 1]
            j = rng.integers(0, nA, size=len(pos))
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
                a = self.event_activity.get(int(e))
                if a is not None and a in self.act_index:
                    out[k] = float((uvec * self.E[self.act_index[a]]).sum())
                else:
                    out[k] = float(self.fallback.score(user_id, np.array([e]))[0])
        return out
