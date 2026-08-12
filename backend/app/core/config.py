from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Kanban API"
    VERSION: str = "1.0.0"

    DATABASE_URL: str = "mysql+pymysql://kanban:kanban@db:3306/kanban"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "kanban"
    JWT_AUDIENCE: str = "kanban-app"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ALLOW_REGISTRATION: bool = True

    RATE_LIMIT_MAX: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
