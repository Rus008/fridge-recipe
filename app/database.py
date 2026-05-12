from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase
import logging

from .configs import get_config
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)
config = get_config()

engine = create_engine(
    config.SYNC_DATABASE_URL,
    poolclass=NullPool,
    echo=config.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in config.SYNC_DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


async_engine = create_async_engine(
    config.DATABASE_URL,
    echo=config.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
