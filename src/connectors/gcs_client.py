from google.cloud import storage
from typing import List, Optional

class GCSClient:
    def __init__(self, project_id: str):
        self.client = storage.Client(project=project_id)

    def list_files(self, bucket_name: str, prefix: Optional[str] = None) -> List[str]:
        """Lists files in a GCS bucket."""
        blobs = self.client.list_blobs(bucket_name, prefix=prefix)
        return [blob.name for blob in blobs]

    def read_file(self, bucket_name: str, blob_name: str) -> bytes:
        """Reads a file from GCS."""
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_bytes()
