from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CNIS_", env_file=".env")

    api_key: str = "changeme"
    max_upload_size_mb: int = 16
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: str = "*"


settings = Settings()
