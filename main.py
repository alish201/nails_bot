import asyncio
import sys
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from config.settings import settings
from app.database.database import db_manager
from app.middlewares.auth import AuthMiddleware, DatabaseMiddleware, LoggingMiddleware
from app.handlers import common, admin, master


async def main():
    """Основная функция запуска бота"""
    
    # Настройка логирования
    logger.remove()
    logger.add(
        "logs/bot.log",
        level=settings.LOG_LEVEL,
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="{time:HH:mm:ss} | {level} | {message}"
    )
    
    # Отключаем стандартный логгер aiogram
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    
    logger.info("Starting Hair Analysis Bot...")
    
    # Инициализируем бота
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализируем диспетчер
    dp = Dispatcher()
    
    # Подключаем middleware
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Подключаем роутеры
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(master.router)
    
    logger.info("Bot configuration complete")
    
    try:
        # Проверяем подключение к базе данных
        async for session in db_manager.get_session():
            logger.info("Database connection successful")
            break
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        logger.info(f"Bot started: @{bot_info.username}")
        
        # Запускаем поллинг
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        # Закрываем соединения
        await bot.session.close()
        await db_manager.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
