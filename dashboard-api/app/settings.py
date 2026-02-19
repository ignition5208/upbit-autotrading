from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    version: str = "1.8-0001"

    # security
    api_key: str | None = Field(default=None, alias="API_KEY")

    # DB
    database_url: str = Field(
        default="mysql+pymysql://root:password@localhost:3306/trading",
        alias="DATABASE_URL",
    )

    # CORS
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["*"])

    # orchestrator
    trader_compose_project_dir: str | None = Field(default=None, alias="TRADER_COMPOSE_PROJECT_DIR")
    trader_service_template: str = Field(default="trader-template", alias="TRADER_SERVICE_TEMPLATE")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
