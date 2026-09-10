import os
from google.cloud import storage
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

_client = None
_bucket = None


def get_storage_client():
    global _client
    if _client is not None:
        return _client

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        _client = storage.Client(credentials=credentials)
    else:
        _client = storage.Client()

    return _client


def get_bucket():
    global _bucket
    if _bucket is not None:
        return _bucket

    bucket_name = os.getenv("GCS_BUCKET_NAME", "videos_validacion")
    _bucket = get_storage_client().bucket(bucket_name)
    return _bucket


def build_blob_name(country, efirmauser, filename):
    return f"{country.upper()}/{efirmauser}/{filename}"


def upload_file(local_path, blob_name):
    try:
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        return f"gs://{bucket.name}/{blob_name}"
    except Exception as e:
        print(f"[GCS] Error al subir {blob_name}: {e}")
        return None