import os
from google.cloud import storage

_gcs_client = None
_bucket = None

def get_gcs_client():
    global _gcs_client
    
    if _gcs_client is None:
        try:
            # Check if running on Cloud Run (has default credentials)
            if os.getenv('K_SERVICE'):  # Cloud Run sets this environment variable
                print("Running on Cloud Run - using default credentials")
                _gcs_client = storage.Client()
            
            # Check if service account key file is provided (local development)
            elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
                credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if os.path.exists(credentials_path):
                    print(f"Using service account key: {credentials_path}")
                    _gcs_client = storage.Client.from_service_account_json(credentials_path)
                else:
                    print(f"Service account key not found: {credentials_path}")
                    _gcs_client = None
            
            # Try default credentials (works on Cloud Run, GCE, local gcloud auth)
            else:
                print("Trying default credentials...")
                try:
                    _gcs_client = storage.Client()
                    print("Using default credentials")
                except Exception as e:
                    print(f"Could not initialize GCS client: {e}")
                    _gcs_client = None
        
        except Exception as e:
            print(f"GCS client initialization failed: {e}")
            _gcs_client = None
    
    return _gcs_client

def get_bucket():
    global _bucket
    
    if _bucket is None:
        client = get_gcs_client()
        
        if client:
            bucket_name = os.getenv('GCS_BUCKET_NAME')
            
            if bucket_name:
                try:
                    _bucket = client.bucket(bucket_name)
                    # Test if bucket is accessible
                    if _bucket.exists():
                        print(f"Connected to bucket: {bucket_name}")
                    else:
                        print(f"Bucket does not exist: {bucket_name}")
                        _bucket = None
                except Exception as e:
                    print(f"Could not access bucket {bucket_name}: {e}")
                    _bucket = None
            else:
                print("GCS_BUCKET_NAME not set")
                _bucket = None
        else:
            print("GCS client not available")
    
    return _bucket
