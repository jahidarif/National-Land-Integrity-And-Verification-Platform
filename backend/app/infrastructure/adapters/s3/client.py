from app.core.config import settings


def create_s3_client():
    """Shared boto3 client factory; uses explicit credentials only when configured."""
    import boto3
    kwargs = {"service_name": "s3", "region_name": settings.s3_region}
    if settings.s3_endpoint_url: kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.s3_access_key_id: kwargs["aws_access_key_id"] = settings.s3_access_key_id
    if settings.s3_secret_access_key: kwargs["aws_secret_access_key"] = settings.s3_secret_access_key
    return boto3.client(**kwargs)
