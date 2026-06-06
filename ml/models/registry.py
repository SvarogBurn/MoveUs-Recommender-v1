"""Model factory list (instantiate fresh per run)."""
from ml.models.random_rec import RandomRec
from ml.models.popularity import PopularityRec
from ml.models.logreg import LogRegRec
from ml.models.lgbm_ranker import LGBMRankerRec
from ml.models.fm import FMRec
from ml.models.bpr_mf import BPRMFRec
from ml.models.lightgcn import LightGCNRec
from ml.models.deepfm import DeepFMRec


def all_models(fast: bool = False):
    e = 2 if fast else 15
    ec = 3 if fast else 20
    return [
        RandomRec(seed=0),
        PopularityRec(),
        LogRegRec(),
        LGBMRankerRec(),
        FMRec(epochs=e),
        BPRMFRec(epochs=ec),
        LightGCNRec(epochs=ec),
        DeepFMRec(epochs=e),
    ]
