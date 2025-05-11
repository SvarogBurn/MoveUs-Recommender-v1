import datetime
import enum
from core.gcs_client import bucket
from core.settings import CONFIG

class Method(enum.Enum):
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"

def generate_signed_url(
        blob_name: str, 
        method: Method,
        expiration_minutes: int = 5,
        ):
    blob = bucket.blob(blob_name) 

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expiration_minutes),
        method=method.value,
    )

    return url

