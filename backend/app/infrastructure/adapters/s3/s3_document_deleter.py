from app.core.config import settings
from app.infrastructure.adapters.s3.client import create_s3_client
from app.domain.ports.i_document_deleter import IDocumentDeleter
class S3DocumentDeleter(IDocumentDeleter):
    def __init__(self): self.client = create_s3_client()
    def delete(self, storage_key: str) -> None:
        self.client.delete_object(Bucket=settings.s3_bucket, Key=storage_key)
