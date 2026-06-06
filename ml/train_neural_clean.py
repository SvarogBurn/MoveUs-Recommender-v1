#!/usr/bin/env python3
"""
DEPRECATED: train_neural.py has been superseded by run_benchmark.py

This file trained only NCF + Two-Tower with the old LOO@99 protocol.
The seminar benchmark (run_benchmark.py) now implements:
  - 7 models: Random, Popularity, LightGBM, FM, BPR-MF, LightGCN, DeepFM
  - Correct metrics: Weighted NDCG@10, Recall@10, MRR
  - Evaluation slices: overall, cold users, warm users, new events

Use instead: python ml/models/run_benchmark.py
"""

import sys

if __name__ == "__main__":
    print("ERROR: train_neural.py is deprecated.")
    print("Use: python -m ml.models.run_benchmark")
    sys.exit(1)
