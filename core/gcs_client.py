from google.cloud import storage
from core.settings import CONFIG
import datetime

# Create a global or shared client instance (recommended)
gcs_client = storage.Client('robust-builder-457115-r6 ')
bucket = gcs_client.bucket(CONFIG['GCS_BUCKET_NAME'])
