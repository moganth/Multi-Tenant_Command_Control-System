import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

load_dotenv()

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Multi-Tenant Command & Control System"

    # Database Configuration
    MONGODB_URL: str = os.getenv("MONGO_URL")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME")

    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL")

    # MQTT Configuration
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT")) # Must convert to int
    MQTT_USERNAME: Optional[str] = os.getenv("MQTT_USERNAME")
    MQTT_PASSWORD: Optional[str] = os.getenv("MQTT_PASSWORD")

    # Supabase Configuration - Using os.getenv() with proper type annotations
    SUPABASE_DB_HOST: str = os.getenv("SUPABASE_DB_HOST")
    SUPABASE_DB_PORT: str = os.getenv("SUPABASE_DB_PORT")
    SUPABASE_DB_NAME: str = os.getenv("SUPABASE_DB_NAME")
    SUPABASE_DB_USER: str = os.getenv("SUPABASE_DB_USER")
    SUPABASE_DB_PASSWORD: str = os.getenv("SUPABASE_DB_PASSWORD")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH: str = "multi-tenant-d2b35-firebase-adminsdk-fbsvc-b3c5a315db.json"

    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Celery Configuration
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()