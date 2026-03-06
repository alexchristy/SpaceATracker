from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    DATABASE_URL: str = (
        "postgresql+asyncpg://spaceatracker:password@localhost:5432/spaceatracker"
    )
    LOG_LEVEL: str = "INFO"

    # SeaweedFS / S3 Settings
    S3_ENDPOINT_URL: str = "http://localhost:8333"
    S3_ACCESS_KEY: str = "some_access_key"
    S3_SECRET_KEY: str = "some_secret_key"
    S3_BUCKET_NAME: str = "terminals"

    # Discovery Scraper Settings
    MAIN_DIRECTORY_URL: str = (
        "https://www.amc.af.mil/AMC-Travel-Site/AMC-Space-Available-Travel-Page/"
    )


settings = Settings()
