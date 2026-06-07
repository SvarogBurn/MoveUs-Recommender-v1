"""Django management command to retrain the recommender and save the best model.

Usage:
    python manage.py retrain
    python manage.py retrain --data-dir ml/data --results-dir ml/results/llm
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Retrain all recommendation models and save the best one to ml/models_store/"

    def add_arguments(self, parser):
        parser.add_argument("--data-dir",    default=None, help="Path to dataset CSVs")
        parser.add_argument("--results-dir", default=None, help="Where to write benchmark results")
        parser.add_argument("--fast",        action="store_true", help="Skip slow models")

    def handle(self, *args, **options):
        from ml.models.run_benchmark import run_benchmark

        self.stdout.write("Starting benchmark + retrain...")
        results = run_benchmark(
            data_dir=options["data_dir"],
            results_dir=options["results_dir"],
            fast=options["fast"],
        )
        best = max(results, key=lambda m: results[m].get("overall", {}).get("ndcg@10", 0.0))
        ndcg = results[best]["overall"]["ndcg@10"]
        self.stdout.write(self.style.SUCCESS(
            f"Done. Best model: {best} (NDCG@10={ndcg:.4f}) saved to ml/models_store/best_model.pkl"
        ))

        # reset singleton so the next request picks up the new model
        from ml.recommender_service import RecommenderService
        RecommenderService._instance = None
