from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SafeHer"
    APP_ENV: str = "development"
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMS_API_KEY: str = ""
    SMS_SENDER_ID: str = ""
    CORS_ORIGINS: str = "http://localhost:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
