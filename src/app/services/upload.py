import re
import uuid
from pathlib import PurePosixPath

from app.core.config import get_settings
from app.schemas.upload import PresignedUploadResponse

settings = get_settings()

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def normalize_upload_folder(folder: str) -> str:
    normalized = folder.strip().lower()
    normalized = re.sub(r"[^a-z0-9/_-]+", "-", normalized)
    normalized = normalized.strip("/-")
    return normalized or "uploads"


def get_file_extension(filename: str, content_type: str) -> str:
    suffix = PurePosixPath(filename).suffix.lower()
    allowed_suffix = ALLOWED_IMAGE_CONTENT_TYPES[content_type]

    if suffix in ALLOWED_IMAGE_CONTENT_TYPES.values():
        return suffix

    return allowed_suffix


def create_r2_client():
    import boto3
    from botocore.client import Config

    if not all(
        [
            settings.r2_endpoint_url,
            settings.r2_access_key_id,
            settings.r2_secret_access_key,
            settings.r2_bucket_name,
        ]
    ):
        raise ValueError("R2 is not configured.")

    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def create_presigned_upload_url(
    *,
    folder: str,
    filename: str,
    content_type: str,
) -> PresignedUploadResponse:
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValueError("Unsupported image content type.")

    normalized_folder = normalize_upload_folder(folder)
    extension = get_file_extension(filename, content_type)
    r2_key = f"{normalized_folder}/{uuid.uuid4().hex}{extension}"

    client = create_r2_client()
    upload_url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.r2_bucket_name,
            "Key": r2_key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.r2_presigned_url_expire_seconds,
        HttpMethod="PUT",
    )

    public_base_url = settings.r2_public_base_url.rstrip("/")
    public_url = f"{public_base_url}/{r2_key}" if public_base_url else ""

    return PresignedUploadResponse(
        upload_url=upload_url,
        r2_key=r2_key,
        public_url=public_url,
        headers={"Content-Type": content_type},
        expires_in=settings.r2_presigned_url_expire_seconds,
    )


def delete_r2_object(r2_key: str) -> None:
    if not r2_key:
        return

    client = create_r2_client()
    try:
        client.delete_object(Bucket=settings.r2_bucket_name, Key=r2_key)
    except Exception as exc:
        raise ValueError("R2 object delete failed.") from exc


def delete_r2_objects(r2_keys: list[str]) -> None:
    keys = [r2_key for r2_key in r2_keys if r2_key]
    if not keys:
        return

    client = create_r2_client()
    for index in range(0, len(keys), 1000):
        chunk = keys[index : index + 1000]
        try:
            client.delete_objects(
                Bucket=settings.r2_bucket_name,
                Delete={
                    "Objects": [{"Key": r2_key} for r2_key in chunk],
                    "Quiet": True,
                },
            )
        except Exception as exc:
            raise ValueError("R2 objects delete failed.") from exc


def delete_r2_object(r2_key: str) -> None:
    if not r2_key:
        return

    client = create_r2_client()
    client.delete_object(Bucket=settings.r2_bucket_name, Key=r2_key)


def delete_r2_objects(r2_keys: list[str]) -> None:
    keys = [{"Key": r2_key} for r2_key in r2_keys if r2_key]
    if not keys:
        return

    client = create_r2_client()
    client.delete_objects(
        Bucket=settings.r2_bucket_name,
        Delete={"Objects": keys, "Quiet": True},
    )
