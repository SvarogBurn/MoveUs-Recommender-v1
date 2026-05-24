import enum
import uuid
from abc import ABC, abstractmethod
from types import MappingProxyType

from django.conf import settings

from core.redis_client import get_sync, set_sync
from shared.errors.mu_error import MUError, MUErrorCode

# Storage paths
ATTACHMENT_PATH = "attachment"
PROFILE_PICTURES_PATH = "profile-pictures"
EVENT_PICTURES_PATH = "event-pictures"
POST_PICTURES_PATH = "post-pictures"

REDIS_KEY_FORMAT = "attachment:{id}:creator"
MUST_REVALIDATE_HEADERS = MappingProxyType({"cache-control": "must-revalidate"})

# Content-Type is bound into the signed URL so GCS rejects a PUT whose
# request header doesn't match. Size is verified server-side after upload
# (validate_attachment) and via bucket lifecycle policy for picture flows
# that have no validate step.
ALLOWED_PICTURE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)
ALLOWED_ATTACHMENT_CONTENT_TYPES = ALLOWED_PICTURE_CONTENT_TYPES | frozenset(
    {"image/gif"}
)

format_key = lambda id: REDIS_KEY_FORMAT.format(id=id)


class Method(enum.Enum):
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"


def _check_content_type(content_type: str, allowed: frozenset[str]) -> None:
    if content_type not in allowed:
        raise MUError(MUErrorCode.UNSUPPORTED_CONTENT_TYPE)


class StorageBackend(ABC):
    @abstractmethod
    def generate_signed_url(
        self,
        blob_name: str,
        method: Method,
        expiration_minutes: int = 5,
        headers: dict = None,
    ) -> str:
        """Generate a signed URL for a blob."""

    @abstractmethod
    def blob_exists(self, blob_name: str) -> bool:
        """Check whether a blob exists."""

    @abstractmethod
    def blob_size(self, blob_name: str) -> int | None:
        """Return the size of a blob in bytes, or None if it doesn't exist."""

    def generate_attachment_upload_url(
        self, user_id: int, content_type: str
    ) -> tuple[str, str]:
        _check_content_type(content_type, ALLOWED_ATTACHMENT_CONTENT_TYPES)
        attachment_id = uuid.uuid4()
        url = self.generate_signed_url(
            f"{ATTACHMENT_PATH}/{attachment_id}",
            Method.PUT,
            settings.ATTACHMENT_UPLOAD_EXPIRATION_MINUTES,
            headers={"content-type": content_type},
        )
        set_sync(
            format_key(attachment_id),
            user_id,
            settings.ATTACHMENT_UPLOAD_EXPIRATION_MINUTES * 60,
        )
        return (attachment_id, url)

    def generate_attachment_url(self, attachment_id: str) -> str:
        return self.generate_signed_url(
            f"{ATTACHMENT_PATH}/{attachment_id}",
            Method.GET,
            settings.ATTACHMENT_URL_EXPIRATION_DAYS * 24 * 60,
        )

    def validate_attachment(self, attachment_id: str, user_id: int) -> None:
        key = format_key(attachment_id)
        owner = get_sync(key)
        if owner is None or owner != str(user_id):
            raise MUError(MUErrorCode.ATTACHMENT_NOT_OWNED)

        blob_name = f"{ATTACHMENT_PATH}/{attachment_id}"
        size = self.blob_size(blob_name)
        if size is None:
            raise MUError(MUErrorCode.ATTACHMENT_NOT_UPLOADED)
        if size > settings.MAX_ATTACHMENT_BYTES:
            raise MUError(MUErrorCode.ATTACHMENT_TOO_LARGE)

    def generate_profile_picture_url(self, user_id: int, content_type: str) -> str:
        _check_content_type(content_type, ALLOWED_PICTURE_CONTENT_TYPES)
        return self.generate_signed_url(
            f"{PROFILE_PICTURES_PATH}/{user_id}",
            Method.PUT,
            headers={**MUST_REVALIDATE_HEADERS, "content-type": content_type},
        )

    def generate_event_picture_url(self, event_id: int, content_type: str) -> str:
        _check_content_type(content_type, ALLOWED_PICTURE_CONTENT_TYPES)
        return self.generate_signed_url(
            f"{EVENT_PICTURES_PATH}/{event_id}",
            Method.PUT,
            headers={**MUST_REVALIDATE_HEADERS, "content-type": content_type},
        )

    def generate_post_picture_url(self, post_id: int, content_type: str) -> str:
        _check_content_type(content_type, ALLOWED_PICTURE_CONTENT_TYPES)
        return self.generate_signed_url(
            f"{POST_PICTURES_PATH}/{post_id}",
            Method.PUT,
            headers={"content-type": content_type},
        )
