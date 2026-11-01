from app.core.config import settings
from app.infrastructure.adapters.s3.client import create_s3_client
from app.domain.ports.i_document_reader import IDocumentReader
class S3DocumentReader(IDocumentReader):
    def __init__(self): self.client = create_s3_client()
    def read(self, storage_key: str) -> bytes:
        return self.client.get_object(Bucket=settings.s3_bucket, Key=storage_key)["Body"].read()
