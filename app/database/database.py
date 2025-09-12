import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from config.settings import settings


class Base(DeclarativeBase):
    pass


class DatabaseManager:
    def __init__(self):
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()

    async def close(self):
        await self.engine.dispose()


# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()


# Dependency для получения сессии базы данных
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in db_manager.get_session():
        yield session
