from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    version: str = Field(default="v2.0-0001")
    log_level: str = Field(default="INFO")

    mysql_host: str = Field(default="mariadb", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_database: str = Field(default="upbit_ats", alias="MYSQL_DATABASE")
    mysql_user: str = Field(default="upbit", alias="MYSQL_USER")
    mysql_password: str = Field(default="upbitpass", alias="MYSQL_PASSWORD")

    cors_allow_origins: str | list[str] = Field(default="*", alias="CORS_ALLOW_ORIGINS")
    disable_api_key: bool = Field(default=True, alias="DISABLE_API_KEY")

    crypto_master_key: str = Field(default="", alias="CRYPTO_MASTER_KEY")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    docker_network: str = Field(default="ats-net", alias="DOCKER_NETWORK")
    paper_protect_hours: int = Field(default=24, alias="PAPER_PROTECT_HOURS")
    daily_loss_limit_pct: float = Field(default=0.05, alias="DAILY_LOSS_LIMIT_PCT")
    consecutive_loss_limit: int = Field(default=5, alias="CONSECUTIVE_LOSS_LIMIT")
