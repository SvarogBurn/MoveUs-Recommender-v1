"""LightGCN (torch) over a recurring-node graph: users x activities plus the
user-user follow graph. Events never recur, so items are keyed on the event's
*activity*; a brand-new event is scored via its activity node, which message
passing has already embedded. Unseen users fall back to popularity."""
import numpy as np
import torch

from ml.models.popularity import PopularityRec


class LightGCNRec:
    name = "LightGCN"

    def __init__(self, dim=32, layers=2, epochs=20, lr=0.05, seed=0):
        self.dim, self.layers, self.epochs, self.lr, self.seed = dim, layers, epochs, lr, seed

    def fit(self, ctx):
        self.fc = ctx.features
        self.final = None
        self.fallback = PopularityRec(); self.fallback.fit(ctx)
        self.event_activity = {int(e): int(a) for e, a in
                               zip(ctx.events["event_id"], ctx.events["activity_id"])}
        acts = sorted(set(self.event_activity.values()))
        self.act_index = {a: i for i, a in enumerate(acts)}

        torch.manual_seed(self.seed); rng = np.random.default_rng(self.seed)
        uidx = self.fc.user_index
        nU, nA = len(uidx), len(self.act_index)
        # user -> activity edges from train attendances
        pos = [(uidx[int(r.user_id)], self.act_index[self.event_activity[int(r.event_id)]])
               for r in ctx.train.itertuples(index=False)
               if r.signal_type != "leave" and int(r.user_id) in uidx
               and int(r.event_id) in self.event_activity]
        if not pos or nU == 0 or nA == 0:
            self.U = self.E = None; return
        pos = np.array(pos)
        n = nU + nA

        # bipartite user<->activity edges (activity nodes offset by nU)
        rows = [pos[:, 0], nU + pos[:, 1]]
        cols = [nU + pos[:, 1], pos[:, 0]]
        # user<->user follow edges (recurring social structure)
        follows = getattr(ctx, "follows", None)
        if follows is not None and len(follows):
            f = np.array([(uidx[int(a)], uidx[int(b)])
                          for a, b in zip(follows["follower_id"], follows["following_id"])
                          if int(a) in uidx and int(b) in uidx], dtype=int)
            if len(f):
                rows += [f[:, 0], f[:, 1]]; cols += [f[:, 1], f[:, 0]]
        rows = np.concatenate(rows); cols = np.concatenate(cols)

        deg = np.bincount(rows, minlength=n).astype(float)
        dinv = 1.0 / np.sqrt(np.maximum(deg, 1.0))
        vals = dinv[rows] * dinv[cols]
        with torch.sparse.check_sparse_tensor_invariants(False):
            A = torch.sparse_coo_tensor(np.vstack([rows, cols]),
                                        torch.tensor(vals, dtype=torch.float32),
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
            j = torch.tensor(nU + rng.integers(0, nA, size=len(pos)))
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
        if self.final is None or int(user_id) not in self.fc.user_index:
            return self.fallback.score(user_id, cand)
        u = self.fc.user_index[int(user_id)]
        out = np.zeros(len(cand))
        with torch.no_grad():
            uvec = self.final[u]
            for k, e in enumerate(cand):
                a = self.event_activity.get(int(e))
                if a is not None and a in self.act_index:
                    out[k] = float((uvec * self.final[self.nU + self.act_index[a]]).sum())
                else:
                    out[k] = float(self.fallback.score(user_id, np.array([e]))[0])
        return out
