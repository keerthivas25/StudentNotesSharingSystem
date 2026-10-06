import os
from pathlib import Path

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file if it exists
dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)

class Config:
    """Base application configuration."""
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-college-project-secret-key-2026')
    
    # Database Configuration (MySQL / RDS)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_NAME = os.getenv('DB_NAME', 'student_notes')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')
    AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', '')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')

    # File Upload Restrictions
    # Maximum upload size: 25 MB
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf', 'ppt', 'pptx', 'doc', 'docx', 'txt', 'csv'}

    # Local Storage fallback directory (useful for testing before configuring AWS S3)
    LOCAL_STORAGE_DIR = BASE_DIR / 'local_storage'

    # Determine if local storage mode should be used:
    # Explicitly enabled via USE_LOCAL_STORAGE=true OR
    # bucket name is not configured / placeholder
    _use_local_env = os.getenv('USE_LOCAL_STORAGE', '').lower()
    if _use_local_env in ('true', '1', 'yes'):
        USE_LOCAL_STORAGE = True
    elif not AWS_S3_BUCKET or AWS_S3_BUCKET == 'your-bucket-name':
        USE_LOCAL_STORAGE = True
    else:
        USE_LOCAL_STORAGE = False
