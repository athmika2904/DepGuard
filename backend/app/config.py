"""Optional application settings.

The scan API does not require GitHub or MongoDB credentials to start.
Those integrations can read these values when they are configured.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_uri: str | None = None
    github_app_id: str | None = None
    github_private_key_path: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
