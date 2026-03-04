from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scraper.core.config import settings

# Create async SQLAlchemy engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_LEVEL == "DEBUG",
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db_session():
    """Dependency provider for async database sessions."""
    async with AsyncSessionFactory() as session:
        yield session


async def init_db() -> None:
    """Initialize database tables for local development."""
    import core.models.flight

    # Import models so they are registered with Base metadata
    import core.models.location  # noqa
    from core.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
