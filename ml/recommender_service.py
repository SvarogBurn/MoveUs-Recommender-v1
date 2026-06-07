#!/usr/bin/env python3
"""Production recommender service — loads best model and serves predictions.

Usage in Django:
    from ml.recommender_service import RecommenderService
    
    service = RecommenderService()
    event_ids = [1, 2, 3, ...]
    scores = service.score(user_id=123, event_ids=event_ids)
    ranked_events = sorted(zip(event_ids, scores), key=lambda x: -x[1])
"""

import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


class RecommenderService:
    """Singleton-like service to load and serve recommendations."""
    
    _instance: Optional["RecommenderService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.model = None
        self.model_name = None
        self.feature_context = None
        self._load_best_model()
    
    def _load_best_model(self):
        """Load best trained model from ml/models_store/."""
        models_dir = Path(__file__).parent / "models_store"
        best_model_path = models_dir / "best_model.pkl"
        metadata_path = models_dir / "best_model_metadata.txt"
        
        if not best_model_path.exists():
            print(f"WARNING: No best model found at {best_model_path}")
            print("Run: python ml/models/run_benchmark.py")
            return
        
        try:
            with open(best_model_path, "rb") as f:
                self.model = pickle.load(f)
            
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    self.model_name = f.read().strip()
            else:
                self.model_name = "unknown"
            
            print(f"✓ Loaded model: {self.model_name}")
        except Exception as e:
            print(f"ERROR loading model: {e}")
            self.model = None
    
    def score(self, user_id: int, event_ids: list) -> np.ndarray:
        """Score events for a user. Returns array of scores (higher = better).
        
        Args:
            user_id: User ID
            event_ids: List of event IDs to score
        
        Returns:
            np.ndarray of scores, same length as event_ids
        """
        if self.model is None:
            # Fallback: equal scores for all events
            return np.ones(len(event_ids)) / len(event_ids)
        
        try:
            scores = self.model.score(int(user_id), np.asarray(event_ids))
            return np.asarray(scores, dtype=float)
        except Exception as e:
            print(f"ERROR scoring: {e}")
            return np.ones(len(event_ids)) / len(event_ids)
    
    def is_ready(self) -> bool:
        """Check if model is loaded and ready."""
        return self.model is not None


def get_recommender() -> RecommenderService:
    """Get singleton recommender instance."""
    return RecommenderService()
