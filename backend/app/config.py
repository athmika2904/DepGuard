import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    mongodb_uri: str = Field(..., env="MONGODB_URI")
    github_app_id: str = Field(..., env="GITHUB_APP_ID")
    github_private_key_path: str = Field(..., env="GITHUB_PRIVATE_KEY_PATH")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
