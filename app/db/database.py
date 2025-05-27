from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_scoped_session
from sqlalchemy.orm import sessionmaker
from app.config import settings
import asyncio
from fastapi import Depends

# Create async SQLite engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    future=True
)

# Create async session factory
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# This is a proper async dependency for FastAPI
async def get_db():
    """Dependency for FastAPI to get a database session"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()