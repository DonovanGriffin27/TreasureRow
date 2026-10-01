# utils/s3.py
# The Vault Campus Marketplace
# Created by Day Ekoi - Iteration 5 4/10/26
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


def _save_locally(file, folder):
    """Save an uploaded file under static/uploads/<folder>/ and return its URL path."""
    ext = file.filename.rsplit(".", 1)[-1].lower()
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
    """
    if USE_LOCAL_STORAGE:
        try:
            return _save_locally(file, folder)
        except Exception as e:
            print(f"Local upload error: {e}")
            return None

    try:
        # generate unique filename
        ext = file.filename.rsplit(".", 1)[-1].lower()
        filename = f"{folder}/{uuid.uuid4().hex}.{ext}"

        # upload to S3 - bucket policy handles public read access
        s3_client.upload_fileobj(
            file,
            BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": file.content_type}
        )

        # return public URL
        url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{filename}"
        return url

    except Exception as e:
        print(f"S3 upload error: {e}")
        return None