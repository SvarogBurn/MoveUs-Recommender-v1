import os
from google.cloud import storage

_gcs_client = None
_bucket = None

def get_gcs_client():
    global _gcs_client
    if _gcs_client is None:
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # Only initialize if credentials are provided
        if credentials_path and os.path.exists(credentials_path):
            _gcs_client = storage.Client.from_service_account_json(credentials_path)
            print("✓ GCS client initialized")
        else:
            print("⚠ GCS not configured - using local file storage")
            _gcs_client = None
    
    return _gcs_client

def get_bucket():
    global _bucket
    if _bucket is None:
        client = get_gcs_client()
        if client:
            bucket_name = os.getenv('GCS_BUCKET_NAME')
            if bucket_name:
                _bucket = client.bucket(bucket_name)
    
    return _bucket
