from google.cloud import storage

from core.settings import CONFIG

gcs_client = storage.Client.from_service_account_json(CONFIG['GOOGLE_APPLICATION_CREDENTIALS'])
bucket = gcs_client.bucket(CONFIG['GCS_BUCKET_NAME'])
