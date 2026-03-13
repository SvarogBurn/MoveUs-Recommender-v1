import datetime
import logging
import os

from google.cloud import storage

from shared.storage.base import Method, StorageBackend

logger = logging.getLogger(__name__)


class GCSStorageBackend(StorageBackend):
    def __init__(self) -> None:
        self._client: storage.Client | None = None
        self._bucket: storage.Bucket | None = None

    def _get_client(self) -> storage.Client | None:
        if self._client is None:
            try:
                if os.getenv("K_SERVICE"):
                    logger.info("Running on Cloud Run - using default credentials")
                    self._client = storage.Client()
                elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                    if os.path.exists(credentials_path):
                        logger.info("Using service account key: %s", credentials_path)
                        self._client = storage.Client.from_service_account_json(
                            credentials_path
                        )
                    else:
                        logger.warning(
                            "Service account key not found: %s", credentials_path
                        )
                else:
                    logger.info("Trying default credentials...")
                    try:
                        self._client = storage.Client()
                        logger.info("Using default credentials")
                    except Exception as e:
                        logger.error("Could not initialize GCS client: %s", e)
            except Exception as e:
                logger.error("GCS client initialization failed: %s", e)

        return self._client

    def _get_bucket(self) -> storage.Bucket | None:
        if self._bucket is None:
            client = self._get_client()
            if client:
                bucket_name = os.getenv("STORAGE_BUCKET_NAME")
                if bucket_name:
                    try:
                        self._bucket = client.bucket(bucket_name)
                        if self._bucket.exists():
                            logger.info("Connected to bucket: %s", bucket_name)
                        else:
                            logger.warning("Bucket does not exist: %s", bucket_name)
                            self._bucket = None
                    except Exception as e:
                        logger.error("Could not access bucket %s: %s", bucket_name, e)
                else:
                    logger.warning("STORAGE_BUCKET_NAME not set")
            else:
                logger.warning("GCS client not available")

        return self._bucket

    def generate_signed_url(
        self,
        blob_name: str,
        method: Method,
        expiration_minutes: int = 5,
        headers: dict = None,
    ) -> str:
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)

        return blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes),
            method=method.value,
            headers=headers or {},
        )

    def blob_exists(self, blob_name: str) -> bool:
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)
        return blob.exists()
