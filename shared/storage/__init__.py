import enum

from django.conf import settings

from shared.storage.base import StorageBackend

_backend: StorageBackend | None = None


def _get_storage_backend() -> StorageBackend:
    global _backend

    if _backend is None:
        backend_name = getattr(settings, "STORAGE_BACKEND", "gcs")

        if backend_name == "gcs":
            from shared.storage.gcs import GCSStorageBackend

            _backend = GCSStorageBackend()
        else:
            raise ValueError(f"Unknown storage backend: {backend_name}")

    return _backend


storage_backend = _get_storage_backend()
