from pydantic import BaseModel, Field


class PresignedUploadRequest(BaseModel):
    folder: str = Field(default="shrimp", min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)


class ImagePresignedUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)


class PresignedUploadResponse(BaseModel):
    upload_url: str
    r2_key: str
    public_url: str
    method: str = "PUT"
    headers: dict[str, str]
    expires_in: int
