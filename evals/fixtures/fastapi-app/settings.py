from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost/app"
    avatar_service_url: str = "http://localhost:8001"


settings = Settings()
