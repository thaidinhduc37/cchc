import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    def __init__(self):
        self.BASE_DIR = Path(__file__).parent.parent.parent
        
        # Database
        self.DB_PATH = self.BASE_DIR / "database" / "users.db"
        
        # JWT Settings
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this")
        self.TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", 60 * 24))
        self.JWT_ALGORITHM = "HS256"
        
        # API Settings
        self.API_PREFIX = "/api"
        self.API_VERSION = "v1"
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        
        # CORS Settings
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        
        # Security
        self.PASSWORD_MIN_LENGTH = 8
        self.PASSWORD_REQUIRE_SPECIAL = True
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOCKOUT_TIME_MINUTES = 15
        
        # File Upload
        self.UPLOAD_FOLDER = self.BASE_DIR / "uploads"
        self.MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = self.BASE_DIR / "logs" / "app.log"