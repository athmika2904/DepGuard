import os
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    mongodb_uri: str = Field(..., env="MONGODB_URI")
    github_app_id: str = Field(..., env="GITHUB_APP_ID")
    github_private_key_path: str = Field(..., env="GITHUB_PRIVATE_KEY_PATH")
    # Add other settings as needed

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
