"""Model factory list (instantiate fresh per run).

Models as per seminar specification:
  - Baseline: Uniform random, Popularity+Feasibility
  - LightGBM LambdaMART
  - Factorization machines (FM)
  - BPR matrix factorization
  - LightGCN
  - DeepFM
"""
from ml.models.random_rec import RandomRec
from ml.models.popularity import PopularityRec
from ml.models.lgbm_ranker import LGBMRankerRec
from ml.models.fm import FMRec
from ml.models.bpr_mf import BPRMFRec
from ml.models.lightgcn import LightGCNRec
from ml.models.deepfm import DeepFMRec


def all_models(fast: bool = False):
    """Instantiate all models in the seminar benchmark."""
    e = 2 if fast else 15
    ec = 3 if fast else 20
    return [
        RandomRec(seed=0),
        PopularityRec(),
        LGBMRankerRec(),
        FMRec(epochs=e),
        BPRMFRec(epochs=ec),
        LightGCNRec(epochs=ec),
        DeepFMRec(epochs=e),
    ]
