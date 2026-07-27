import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    AGORA_APP_ID: str = ""
    AGORA_PRIMARY_CERTIFICATE: str = ""
    AGORA_WEBHOOK_SECRET: str = ""
    AGORA_CHAT_REST_URL: str = "https://a61.chat.agora.io"
    
    JWT_SECRET: str = "default_secret_key_change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    DATABASE_URL: str = "sqlite:///./agora_test.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
