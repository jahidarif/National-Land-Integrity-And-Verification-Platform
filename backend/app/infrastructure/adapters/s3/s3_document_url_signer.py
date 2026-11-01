from app.core.config import settings
from app.infrastructure.adapters.s3.client import create_s3_client
from app.domain.ports.i_document_url_signer import IDocumentUrlSigner
class S3DocumentUrlSigner(IDocumentUrlSigner):
    def __init__(self): self.client = create_s3_client()
    def sign(self, storage_key: str, filename: str, content_type: str) -> str:
        return self.client.generate_presigned_url("get_object", Params={"Bucket": settings.s3_bucket, "Key": storage_key, "ResponseContentDisposition": f'inline; filename="{filename}"', "ResponseContentType": content_type}, ExpiresIn=settings.s3_presign_expires_seconds)
