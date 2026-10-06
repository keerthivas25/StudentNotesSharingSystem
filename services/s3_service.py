import io
import os
import mimetypes
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config import Config

def get_s3_client():
    """
    Create and return a boto3 S3 client.
    Supports explicit credentials (from .env) or IAM Role (when running on AWS EC2).
    """
    session_kwargs = {
        'region_name': Config.AWS_REGION
    }

    # If explicit credentials are provided and not placeholders, use them.
    # Otherwise, boto3 automatically uses the EC2 IAM Instance Profile role.
    if Config.AWS_ACCESS_KEY_ID and Config.AWS_ACCESS_KEY_ID != 'your-access-key':
        session_kwargs['aws_access_key_id'] = Config.AWS_ACCESS_KEY_ID
        session_kwargs['aws_secret_access_key'] = Config.AWS_SECRET_ACCESS_KEY

    return boto3.client('s3', **session_kwargs)

def generate_s3_key(original_filename):
    """
    Generate a clean and safe S3 object key with prefix 'notes/'.
    Includes a timestamp prefix to avoid filename collisions.
    Example output: 'notes/20261007_021500_machine_learning_unit1.pdf'
    """
    safe_name = secure_filename(original_filename)
    if not safe_name:
        safe_name = "file_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"notes/{timestamp}_{safe_name}"

def upload_file_to_s3(file_obj, s3_key, content_type=None):
    """
    Upload a file-like object to Amazon S3 (or local storage fallback).
    
    Args:
        file_obj: File object (e.g. werkzeug FileStorage or BytesIO)
        s3_key: S3 destination path (e.g. 'notes/filename.pdf')
        content_type: MIME type of the file
        
    Returns:
        bool: True if upload succeeded, raises Exception on failure.
    """
    # Fallback to local storage if running in local mode
    if Config.USE_LOCAL_STORAGE:
        target_path = Config.LOCAL_STORAGE_DIR / s3_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure file pointer is at beginning
        file_obj.seek(0)
        with open(target_path, 'wb') as f:
            f.write(file_obj.read())
        # Reset pointer after reading
        file_obj.seek(0)
        return True

    # Real Amazon S3 Upload via boto3
    s3_client = get_s3_client()
    bucket_name = Config.AWS_S3_BUCKET

    if not bucket_name:
        raise ValueError("AWS_S3_BUCKET is not set in environment variables.")

    extra_args = {}
    if content_type:
        extra_args['ContentType'] = content_type

    try:
        file_obj.seek(0)
        file_content = file_obj.read()
        put_kwargs = {
            'Bucket': bucket_name,
            'Key': s3_key,
            'Body': file_content
        }
        if content_type:
            put_kwargs['ContentType'] = content_type

        s3_client.put_object(**put_kwargs)
        return True
    except (ClientError, NoCredentialsError) as e:
        raise RuntimeError(f"Amazon S3 upload error: {str(e)}")

def download_file_from_s3(s3_key):
    """
    Retrieve a file from Amazon S3 (or local storage fallback).
    
    Args:
        s3_key: S3 object key (e.g. 'notes/filename.pdf')
        
    Returns:
        tuple: (file_stream: io.BytesIO, content_type: str)
    """
    # Fallback to local storage if running in local mode
    if Config.USE_LOCAL_STORAGE:
        target_path = Config.LOCAL_STORAGE_DIR / s3_key
        if not target_path.exists():
            raise FileNotFoundError(f"File not found in local storage: {s3_key}")
        with open(target_path, 'rb') as f:
            content = f.read()
        mime_type, _ = mimetypes.guess_type(target_path)
        return io.BytesIO(content), mime_type or 'application/octet-stream'

    # Real Amazon S3 Download via boto3
    s3_client = get_s3_client()
    bucket_name = Config.AWS_S3_BUCKET

    if not bucket_name:
        raise ValueError("AWS_S3_BUCKET is not set in environment variables.")

    try:
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=s3_key
        )
        body = response['Body'].read()
        content_type = response.get('ContentType', 'application/octet-stream')
        return io.BytesIO(body), content_type
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'NoSuchKey':
            raise FileNotFoundError(f"File not found in S3 bucket: {s3_key}")
        raise RuntimeError(f"Amazon S3 download error: {str(e)}")

def test_s3_connection():
    """
    Test connectivity to Amazon S3 (or verifies local storage directory).
    Returns (status: bool, message: str, storage_type: str).
    """
    if Config.USE_LOCAL_STORAGE:
        try:
            Config.LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            return True, f"Local storage active at {Config.LOCAL_STORAGE_DIR}", "local"
        except Exception as e:
            return False, f"Local storage error: {str(e)}", "local"

    try:
        s3_client = get_s3_client()
        bucket_name = Config.AWS_S3_BUCKET
        # Check bucket existence / access permissions
        s3_client.head_bucket(Bucket=bucket_name)
        return True, f"Amazon S3 bucket '{bucket_name}' accessible in region '{Config.AWS_REGION}'", "s3"
    except Exception as e:
        return False, f"Amazon S3 connection failed: {str(e)}", "s3"
