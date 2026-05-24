import enum
import uuid
from abc import ABC, abstractmethod
from types import MappingProxyType

from core.redis_client import get_sync, set_sync
from shared.errors.mu_error import MUError, MUErrorCode

# Storage paths
ATTACHMENT_PATH = "attachment"
PROFILE_PICTURES_PATH = "profile-pictures"
EVENT_PICTURES_PATH = "event-pictures"
POST_PICTURES_PATH = "post-pictures"

# Redis and cache configuration
REDIS_KEY_FORMAT = "attachment:{id}:creator"
MUST_REVALIDATE_HEADERS = MappingProxyType({"cache-control": "must-revalidate"})
ATTACHMENT_EXPIRATION_MINUTES = 3
ATTACHMENT_URL_EXPIRATION_DAYS = 7

format_key = lambda id: REDIS_KEY_FORMAT.format(id=id)


class Method(enum.Enum):
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"


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

    def generate_attachment_upload_url(self, user_id: int) -> tuple[str, str]:
        attachment_id = uuid.uuid4()
        url = self.generate_signed_url(
            f"{ATTACHMENT_PATH}/{attachment_id}",
            Method.PUT,
            ATTACHMENT_EXPIRATION_MINUTES,
        )
        set_sync(format_key(attachment_id), user_id, ATTACHMENT_EXPIRATION_MINUTES * 60)
        return (attachment_id, url)

    def generate_attachment_url(self, attachment_id: str) -> str:
        return self.generate_signed_url(
            f"{ATTACHMENT_PATH}/{attachment_id}",
            Method.GET,
            ATTACHMENT_URL_EXPIRATION_DAYS * 24 * 60,
        )

    def validate_attachment(self, attachment_id: str, user_id: int) -> None:
        key = format_key(attachment_id)
        owner = get_sync(key)
        if owner is None or owner.decode() != str(user_id):
            raise MUError(MUErrorCode.ATTACHMENT_NOT_OWNED)

        if not self.blob_exists(f"{ATTACHMENT_PATH}/{attachment_id}"):
            raise MUError(MUErrorCode.ATTACHMENT_NOT_UPLOADED)

    def generate_profile_picture_url(self, user_id: int) -> str:
        return self.generate_signed_url(
            f"{PROFILE_PICTURES_PATH}/{user_id}",
            Method.PUT,
            headers=MUST_REVALIDATE_HEADERS,
        )

    def generate_event_picture_url(self, event_id: int) -> str:
        return self.generate_signed_url(
            f"{EVENT_PICTURES_PATH}/{event_id}",
            Method.PUT,
            headers=MUST_REVALIDATE_HEADERS,
        )

    def generate_post_picture_url(self, post_id: int) -> str:
        return self.generate_signed_url(
            f"{POST_PICTURES_PATH}/{post_id}",
            Method.PUT,
        )
