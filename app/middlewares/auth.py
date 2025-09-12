from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from app.database.database import get_db_session
from app.database.models import Owner, Master


class AuthMiddleware(BaseMiddleware):
    """Middleware для проверки авторизации пользователей"""

    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id из события
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        # Получаем сессию базы данных
        db_session = data.get('db_session')
        if not db_session:
            async for session in get_db_session():
                db_session = session
                data['db_session'] = session
                break

        try:
            # Проверяем, является ли пользователь владельцем
            owner_query = select(Owner).where(
                Owner.telegram_id == user_id,
                Owner.is_active == True
            )
            owner_result = await db_session.execute(owner_query)
            owner = owner_result.scalar_one_or_none()

            # Проверяем, является ли пользователь мастером
            master_query = select(Master).options(selectinload(Master.salon)).where(
                Master.telegram_id == user_id,
                Master.is_active == True
            )
            master_result = await db_session.execute(master_query)
            master = master_result.scalar_one_or_none()

            # Добавляем информацию о пользователе в data
            data['user_id'] = user_id
            data['is_owner'] = owner is not None
            data['is_master'] = master is not None
            data['owner'] = owner
            data['master'] = master

            # Логируем попытку доступа
            if owner:
                logger.info(f"Owner {user_id} accessing system")
            elif master:
                logger.info(f"Master {user_id} ({master.name}) accessing system")
            else:
                logger.debug(f"Unregistered user {user_id} accessing system")

            return await handler(event, data)

        except Exception as e:
            logger.error(f"Auth middleware error: {e}")
            # В случае ошибки все равно передаем управление дальше
            data['is_owner'] = False
            data['is_master'] = False
            data['owner'] = None
            data['master'] = None
            return await handler(event, data)


class OwnerOnlyMiddleware(BaseMiddleware):
    """Middleware для ограничения доступа только владельцам"""

    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем, является ли пользователь владельцем
        if not data.get('is_owner', False):
            # Если это сообщение или callback, отправляем уведомление о недостатке прав
            if isinstance(event, Message):
                await event.answer(
                    "❌ У вас нет прав для выполнения этого действия.\n"
                    "Только администраторы могут использовать эту функцию."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "❌ У вас нет прав для выполнения этого действия.",
                    show_alert=True
                )
            return

        return await handler(event, data)


class MasterOnlyMiddleware(BaseMiddleware):
    """Middleware для ограничения доступа только мастерам"""

    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем, является ли пользователь мастером
        if not data.get('is_master', False):
            # Если это сообщение или callback, отправляем уведомление о недостатке прав
            if isinstance(event, Message):
                await event.answer(
                    "❌ Вы не зарегистрированы как мастер.\n"
                    "Обратитесь к администратору салона для получения доступа."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "❌ Вы не зарегистрированы как мастер.",
                    show_alert=True
                )
            return

        return await handler(event, data)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для внедрения сессии базы данных"""

    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if 'db_session' not in data:
            async for db_session in get_db_session():
                data['db_session'] = db_session
                try:
                    return await handler(event, data)
                except Exception as e:
                    await db_session.rollback()
                    logger.error(f"Database error in middleware: {e}")
                    raise
        else:
            return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех событий"""

    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        username = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            username = event.from_user.username

        # Логируем входящее событие
        if isinstance(event, Message):
            if event.text:
                logger.debug(f"Message from {user_id} (@{username}): {event.text}")
            elif event.photo:
                logger.debug(f"Photo from {user_id} (@{username})")
            else:
                logger.debug(f"Other message type from {user_id}: {event.content_type}")
        elif isinstance(event, CallbackQuery):
            logger.debug(f"Callback from {user_id} (@{username}): {event.data}")

        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Handler error for user {user_id}: {e}")
            # Не подавляем исключение, пусть обрабатывается дальше
            raise