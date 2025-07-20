import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # RAGFlow Configuration
    ragflow_api_url: str = os.getenv("RAGFLOW_API_URL", "http://localhost:9380")
    ragflow_api_key: str = os.getenv("RAGFLOW_API_KEY", "")
    
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/pdf_chat_db")
    
    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Application Configuration
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Logging Configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "")
    
    # Security Configuration
    allowed_origins: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))  # 50MB default
    
    # Performance Configuration
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "300"))  # 5 minutes
    
    # Feature Flags
    enable_file_cleanup: bool = os.getenv("ENABLE_FILE_CLEANUP", "True").lower() == "true"
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "False").lower() == "true"
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
    
    class Config:
        env_file = ".env"

settings = Settings()