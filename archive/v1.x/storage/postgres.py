import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

POSTGRES_USER = os.getenv("POSTGRES_USER", "brain")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")  # Allow empty for testing
POSTGRES_DB = os.getenv("POSTGRES_DB", "brain")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

def get_database_url():
    """Get database URL, checking for required password."""
    if not POSTGRES_PASSWORD:
        # Allow empty password in test/CI environments
        if os.getenv("APP_ENV") in ("test", "ci"):
            return f"postgresql+asyncpg://{POSTGRES_USER}:test_password@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        raise ValueError("POSTGRES_PASSWORD environment variable is required")
    return f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

DATABASE_URL = get_database_url()

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session 