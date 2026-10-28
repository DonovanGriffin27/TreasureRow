# utils/s3.py
# The Vault Campus Marketplace
# Handles all S3 image upload functionality
# Updated by Donovan Griffin - 9/8/2026 - added a local-storage fallback for
# local development: when AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, or
# AWS_S3_BUCKET aren't set, uploads save to static/uploads/ instead of S3;
# behavior is unchanged when real AWS credentials are present

import boto3
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

# S3 client setup
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-2")
)

BUCKET_NAME = os.getenv("AWS_S3_BUCKET")
REGION = os.getenv("AWS_REGION", "us-east-2")

# Local-dev fallback: when AWS credentials / bucket are not configured, save
# uploads to static/uploads/ and serve them from there instead of S3.
USE_LOCAL_STORAGE = not (
    os.getenv("AWS_ACCESS_KEY_ID")
    and os.getenv("AWS_SECRET_ACCESS_KEY")
    and BUCKET_NAME
)
LOCAL_UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "static", "uploads")
)


# ---------------------------------------------------------------------------
# Upload validation - added by Donovan Griffin, Iteration 3.
# Before: the folder came straight from the request (../../ wrote files outside
# static/uploads), only the filename extension was checked (a web page renamed
# photo.png was accepted), S3 stored whatever Content-Type the browser sent,
# and there was no size limit.
# ---------------------------------------------------------------------------

class InvalidUpload(ValueError):
    """The uploaded file is not an allowed image (callers return HTTP 400)."""


ALLOWED_FOLDERS = {
    "uploads",
    "listings",
    "returns/damage",
    "storefronts",
    "storefronts/logos",
    "storefronts/banners",
    "storefronts/previews",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB per image


def _detect_image_type(head):
    """Identify an image from its first bytes; returns (extension, content type) or None."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "gif", "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


def validate_image(file, folder):
    """Check the folder and the real file contents; returns (extension, content type)."""
    if folder not in ALLOWED_FOLDERS:
        raise InvalidUpload("Invalid upload folder.")

    stream = file.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    if size > MAX_IMAGE_BYTES:
        raise InvalidUpload("Images must be 5 MB or smaller.")

    detected = _detect_image_type(stream.read(16))
    stream.seek(0)
    if detected is None:
        raise InvalidUpload("File must be a PNG, JPG, GIF, or WebP image.")
    return detected


def _save_locally(file, folder, ext):
    """Save an uploaded file under static/uploads/<folder>/ and return its URL path."""
    filename = f"{uuid.uuid4().hex}.{ext}"
    dest_dir = os.path.join(LOCAL_UPLOAD_DIR, folder)
    os.makedirs(dest_dir, exist_ok=True)
    file.save(os.path.join(dest_dir, filename))
    return f"/static/uploads/{folder}/{filename}"


def upload_image_to_s3(file, folder="uploads"):
    """
    Uploads an image file to S3 and returns the public URL.

    Args:
        file: file object from request.files
        folder: subfolder in S3 bucket (e.g. 'storefronts', 'listings')

    Returns:
        Public URL string (S3 URL, or /static/uploads/... in local-dev mode),
        or None if the upload fails

    Raises:
        InvalidUpload if the folder isn't allowed or the file isn't a real image
    """
    # raises InvalidUpload (-> HTTP 400) for bad folders, non-images, oversize files
    ext, content_type = validate_image(file, folder)

    if USE_LOCAL_STORAGE:
        try:
            return _save_locally(file, folder, ext)
        except Exception as e:
            print(f"Local upload error: {e}")
            return None

    try:
        # generate unique filename (extension from the real file type, not the name)
        filename = f"{folder}/{uuid.uuid4().hex}.{ext}"

        # upload to S3 - bucket policy handles public read access
        # Content-Type is set by the server from the detected type, never by the browser
        s3_client.upload_fileobj(
            file,
            BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": content_type}
        )

        # return public URL
        url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{filename}"
        return url

    except Exception as e:
        print(f"S3 upload error: {e}")
        return None
