from app.core.config import settings
from app.infrastructure.adapters.s3.client import create_s3_client
from app.domain.ports.i_document_uploader import IDocumentUploader
class S3DocumentUploader(IDocumentUploader):
    def __init__(self): self.client = create_s3_client()
    def upload(self, storage_key: str, content: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=settings.s3_bucket, Key=storage_key, Body=content, ContentType=content_type, ServerSideEncryption="AES256")
