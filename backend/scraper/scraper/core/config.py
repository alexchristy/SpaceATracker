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

    # Discovery Scraper Settings
    MAIN_DIRECTORY_URL: str = (
        "https://www.amc.af.mil/AMC-Travel-Site/AMC-Space-Available-Travel-Page/"
    )


settings = Settings()
