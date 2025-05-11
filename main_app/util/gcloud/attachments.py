import uuid

from core.redis_client import get_sync, set_sync
from core.gcs_client import bucket
from core.settings import CONFIG
from main_app.util.gcloud.generate import generate_signed_url, Method
from main_app.graphql.error import MUError, MUErrorCode

format_key = lambda id: f"attachment:{id}:creator"

EXPIRATION_MINUTES = 3

def generate_attachment_upload_url(user_id: int) -> tuple[str, str]:
    attachment_id = uuid.uuid4()
    url = generate_signed_url(
        f'attachment/{attachment_id}',
        Method.PUT,
        EXPIRATION_MINUTES
        )
    set_sync(
        format_key(attachment_id),
        user_id,
        EXPIRATION_MINUTES * 60
    )
    return (attachment_id, url)

def generate_attachment_url(attachment_id: str) -> str:
    return generate_signed_url(
        f'attachment/{attachment_id}',
        Method.GET,
        60 * 24 * 7 # a week 
        )

def validate_attachment(attachment_id: str, user_id: int) -> None:
    key = format_key(attachment_id)
    owner = get_sync(key)
    if owner.decode() != str(user_id):
        raise MUError(MUErrorCode.ATTACHMENT_NOT_OWNED)
    
    blob = bucket.blob(f'attachment/{attachment_id}')
    if not blob.exists():
        raise MUError(MUErrorCode.ATTACHMENT_NOT_UPLOADED)