from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    secret_key: str
    admin_email: str
    admin_password_hash: str

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # Kite Connect
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""

    # LLM
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    ollama_base_url: str = "http://host.docker.internal:11434"

    # Notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Feature flags
    paper_trading_enabled: bool = True
    live_data_enabled: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()  # type: ignore[call-arg]
