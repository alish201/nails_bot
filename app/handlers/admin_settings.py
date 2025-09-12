from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from loguru import logger
from datetime import datetime, timedelta

from app.keyboards.admin_kb import get_settings_keyboard, get_back_button, get_cancel_keyboard, get_admin_main_menu
from app.states.admin_states import AdminStates
from app.database.models import Owner, SystemLog, Analysis, Master, Salon
from app.utils.helpers import format_datetime, hash_password, verify_password

settings_router = Router()


# === ГЛАВНОЕ МЕНЮ НАСТРОЕК ===
@settings_router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message):
    """Меню настроек"""
    await message.answer(
        "⚙️ *Настройки системы*\n\n"
        "Выберите действие:",
        reply_markup=get_settings_keyboard(),
        parse_mode="Markdown"
    )


@settings_router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery):
    """Возврат к настройкам"""
    await callback.message.edit_text(
        "⚙️ *Настройки системы*\n\n"
        "Выберите действие:",
        reply_markup=get_settings_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


# === СМЕНА ПАРОЛЯ ===
@settings_router.callback_query(F.data == "change_password")
async def change_password_start(callback: CallbackQuery, state: FSMContext):
    """Начало смены пароля"""
    await callback.message.edit_text(
        "🔑 *Смена пароля администратора*\n\n"
        "⚠️ *Внимание:*\n"
        "• После смены пароля нужно будет заново авторизоваться\n"
        "• Старый пароль перестанет работать\n"
        "• Убедитесь, что запомните новый пароль\n\n"
        "Введите текущий пароль для подтверждения:",
        reply_markup=get_back_button("back_to_settings"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_current_password)
    await callback.answer()


@settings_router.message(AdminStates.waiting_for_current_password)
async def process_current_password(message: Message, state: FSMContext):
    """Проверка текущего пароля"""
    current_password = message.text.strip()

    # Удаляем сообщение с паролем
    await message.delete()

    from config.settings import settings
    if current_password != settings.ADMIN_PASSWORD:
        await message.answer(
            "❌ Неверный текущий пароль. Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await message.answer(
        "✅ Текущий пароль подтвержден.\n\n"
        "🔑 Введите новый пароль:\n\n"
        "📋 *Требования к паролю:*\n"
        "• Минимум 6 символов\n"
        "• Максимум 50 символов\n"
        "• Может содержать буквы, цифры и символы",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_new_password)


@settings_router.message(AdminStates.waiting_for_new_password)
async def process_new_password(message: Message, state: FSMContext):
    """Обработка нового пароля"""
    new_password = message.text.strip()

    # Удаляем сообщение с паролем
    await message.delete()

    # Проверяем требования к паролю
    if len(new_password) < 6:
        await message.answer(
            "❌ Пароль слишком короткий (минимум 6 символов):",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(new_password) > 50:
        await message.answer(
            "❌ Пароль слишком длинный (максимум 50 символов):",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Проверяем, что пароль не содержит только пробелы
    if not new_password or new_password.isspace():
        await message.answer(
            "❌ Пароль не может состоять только из пробелов:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(new_password=new_password)

    await message.answer(
        "🔄 Подтвердите новый пароль:\n\n"
        "Введите пароль еще раз для подтверждения:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_password_confirmation)


@settings_router.message(AdminStates.waiting_for_password_confirmation)
async def process_password_confirmation(message: Message, state: FSMContext):
    """Подтверждение нового пароля"""
    password_confirmation = message.text.strip()

    # Удаляем сообщение с паролем
    await message.delete()

    data = await state.get_data()
    new_password = data.get('new_password')

    if password_confirmation != new_password:
        await message.answer(
            "❌ Пароли не совпадают. Введите подтверждение еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Здесь обычно бы обновляли пароль в базе данных,
    # но в данной реализации пароль хранится в настройках
    await state.clear()

    await message.answer(
        "⚠️ *Смена пароля*\n\n"
        "Новый пароль подтвержден.\n\n"
        "🔧 *Для применения изменений:*\n"
        "1. Остановите бота\n"
        "2. Измените ADMIN_PASSWORD в файле .env\n"
        "3. Перезапустите бота\n\n"
        "💡 *Альтернативно:* Можете изменить пароль прямо в файле .env и перезапустить бота.\n\n"
        "⚠️ После перезапуска используйте новый пароль для входа.",
        reply_markup=get_admin_main_menu(),
        parse_mode="Markdown"
    )

    logger.info(f"Password change requested by admin {message.from_user.id}")


# === СИСТЕМНЫЕ ЛОГИ ===
@settings_router.callback_query(F.data == "system_logs")
async def system_logs(callback: CallbackQuery, db_session: AsyncSession):
    """Просмотр системных логов"""
    # Получаем последние 15 записей логов
    query = select(SystemLog).order_by(SystemLog.created_at.desc()).limit(15)
    result = await db_session.execute(query)
    logs = result.scalars().all()

    if not logs:
        await callback.message.edit_text(
            "📋 *Системные логи*\n\n"
            "Записи логов не найдены.",
            reply_markup=get_back_button("back_to_settings"),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    logs_text = "📋 *Последние системные логи*\n\n"

    for log in logs[:10]:  # Показываем только 10 последних
        user_info = f"User {log.user_id}" if log.user_id else "System"
        logs_text += (
            f"🕐 {format_datetime(log.created_at)}\n"
            f"👤 {user_info}\n"
            f"📝 {log.action}\n\n"
        )

    if len(logs) > 10:
        logs_text += f"... и еще {len(logs) - 10} записей"

    await callback.message.edit_text(
        logs_text,
        reply_markup=get_back_button("back_to_settings"),
        parse_mode="Markdown"
    )
    await callback.answer()


# === ОБНОВЛЕНИЕ ДАННЫХ ===
@settings_router.callback_query(F.data == "refresh_data")
async def refresh_data(callback: CallbackQuery, db_session: AsyncSession):
    """Обновление данных системы"""

    # Подсчитываем актуальную статистику
    try:
        salons_count = await db_session.scalar(
            select(func.count(Salon.id)).where(Salon.is_active == True)
        )
        masters_count = await db_session.scalar(
            select(func.count(Master.id)).where(Master.is_active == True)
        )
        analyses_count = await db_session.scalar(select(func.count(Analysis.id)))

        # Статистика за сегодня
        today_analyses = await db_session.scalar(
            select(func.count(Analysis.id)).where(
                func.date(Analysis.created_at) == func.current_date()
            )
        )

        # Общие квоты
        total_quota = await db_session.scalar(
            select(func.sum(Salon.quota_limit)).where(Salon.is_active == True)
        ) or 0
        used_quota = await db_session.scalar(
            select(func.sum(Salon.quota_used)).where(Salon.is_active == True)
        ) or 0

        # Проверяем соединение с БД
        await db_session.execute(text("SELECT 1"))

        await callback.message.edit_text(
            f"🔄 *Данные обновлены*\n\n"
            f"📊 *Текущая статистика:*\n"
            f"🏢 Активных салонов: {salons_count}\n"
            f"👤 Активных мастеров: {masters_count}\n"
            f"📸 Всего анализов: {analyses_count}\n"
            f"📅 Анализов сегодня: {today_analyses}\n\n"
            f"💰 *Квоты:*\n"
            f"📊 Общий лимит: {total_quota}\n"
            f"✅ Использовано: {used_quota}\n"
            f"⏳ Остаток: {total_quota - used_quota}\n\n"
            f"🟢 Соединение с БД: OK\n"
            f"🕐 Обновлено: {format_datetime(datetime.now())}",
            reply_markup=get_back_button("back_to_settings"),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error refreshing data: {e}")
        await callback.message.edit_text(
            f"❌ *Ошибка обновления данных*\n\n"
            f"Произошла ошибка при получении данных:\n"
            f"`{str(e)}`\n\n"
            f"Проверьте соединение с базой данных.",
            reply_markup=get_back_button("back_to_settings"),
            parse_mode="Markdown"
        )

    await callback.answer("Данные обновлены!")


# === ОЧИСТКА ЛОГОВ ===
@settings_router.callback_query(F.data == "clear_logs")
async def clear_logs_confirm(callback: CallbackQuery):
    """Подтверждение очистки логов"""
    from app.keyboards.admin_kb import get_confirmation_keyboard

    await callback.message.edit_text(
        "🗑️ *Очистка системных логов*\n\n"
        "⚠️ *Внимание!*\n"
        "Это действие удалит все записи логов старше 30 дней.\n"
        "Данные нельзя будет восстановить.\n\n"
        "Продолжить?",
        reply_markup=get_confirmation_keyboard("clear_logs", 0),
        parse_mode="Markdown"
    )
    await callback.answer()


@settings_router.callback_query(F.data == "confirm_clear_logs_0")
async def clear_logs_execute(callback: CallbackQuery, db_session: AsyncSession):
    """Выполнение очистки логов"""
    try:
        # Удаляем записи логов старше 30 дней
        cutoff_date = datetime.now() - timedelta(days=30)

        result = await db_session.execute(
            text("DELETE FROM system_logs WHERE created_at < :cutoff_date"),
            {"cutoff_date": cutoff_date}
        )

        deleted_count = result.rowcount
        await db_session.commit()

        await callback.message.edit_text(
            f"✅ *Логи очищены*\n\n"
            f"Удалено записей: {deleted_count}\n"
            f"Удалены записи старше: {format_datetime(cutoff_date)}\n\n"
            f"🕐 Выполнено: {format_datetime(datetime.now())}",
            reply_markup=get_back_button("back_to_settings"),
            parse_mode="Markdown"
        )

        logger.info(f"System logs cleared: {deleted_count} records deleted")

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Error clearing logs: {e}")

        await callback.message.edit_text(
            f"❌ *Ошибка очистки логов*\n\n"
            f"Произошла ошибка: `{str(e)}`",
            reply_markup=get_back_button("back_to_settings"),
            parse_mode="Markdown"
        )

    await callback.answer()


@settings_router.callback_query(F.data == "cancel_clear_logs_0")
async def cancel_clear_logs(callback: CallbackQuery):
    """Отмена очистки логов"""
    await callback.message.edit_text(
        "❌ Очистка логов отменена",
        reply_markup=get_back_button("back_to_settings")
    )
    await callback.answer()


# === БЭКАП ДАННЫХ ===
@settings_router.callback_query(F.data == "backup_data")
async def backup_data_info(callback: CallbackQuery):
    """Информация о резервном копировании"""
    await callback.message.edit_text(
        "💾 *Резервное копирование*\n\n"
        "🔧 *Для создания бэкапа базы данных:*\n\n"
        "1. **PostgreSQL:**\n"
        "`pg_dump -h localhost -U postgres hair_analysis_bot > backup.sql`\n\n"
        "2. **Восстановление:**\n"
        "`psql -h localhost -U postgres hair_analysis_bot < backup.sql`\n\n"
        "💡 *Рекомендации:*\n"
        "• Создавайте бэкапы регулярно\n"
        "• Храните бэкапы в надежном месте\n"
        "• Проверяйте целостность бэкапов\n"
        "• Настройте автоматическое создание бэкапов",
        reply_markup=get_back_button("back_to_settings"),
        parse_mode="Markdown"
    )
    await callback.answer()


# === СИСТЕМНАЯ ИНФОРМАЦИЯ ===
@settings_router.callback_query(F.data == "system_info")
async def system_info(callback: CallbackQuery, db_session: AsyncSession):
    """Подробная системная информация"""
    import sys
    import platform
    import psutil
    from datetime import datetime

    try:
        # Информация о системе
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Информация о памяти
        memory = psutil.virtual_memory()
        memory_used = memory.used / (1024 ** 3)  # GB
        memory_total = memory.total / (1024 ** 3)  # GB
        memory_percent = memory.percent

        # Информация о диске
        disk = psutil.disk_usage('/')
        disk_used = disk.used / (1024 ** 3)  # GB
        disk_total = disk.total / (1024 ** 3)  # GB
        disk_percent = (disk.used / disk.total) * 100

        # Время работы системы
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time

        # Информация о базе данных
        db_version = await db_session.scalar(text("SELECT version()"))
        db_version_short = db_version.split()[1] if db_version else "Неизвестно"

        # Размер базы данных
        try:
            db_size_query = text("""
                SELECT pg_size_pretty(pg_database_size('hair_analysis_bot'))
            """)
            db_size = await db_session.scalar(db_size_query) or "Неизвестно"
        except:
            db_size = "Неизвестно"

        # Последняя активность
        last_analysis = await db_session.scalar(
            select(Analysis.created_at).order_by(Analysis.created_at.desc()).limit(1)
        )

        await callback.message.edit_text(
            f"ℹ️ *Подробная системная информация*\n\n"
            f"🤖 *Бот:*\n"
            f"📊 Версия: 1.0.0\n"
            f"🐍 Python: {python_version}\n"
            f"💻 ОС: {platform.system()} {platform.release()}\n\n"
            f"🖥️ *Ресурсы сервера:*\n"
            f"🧠 ОЗУ: {memory_used:.1f}/{memory_total:.1f} GB ({memory_percent:.1f}%)\n"
            f"💾 Диск: {disk_used:.1f}/{disk_total:.1f} GB ({disk_percent:.1f}%)\n"
            f"⏰ Аптайм: {uptime.days} дней {uptime.seconds // 3600} часов\n\n"
            f"🗄️ *База данных:*\n"
            f"📊 PostgreSQL: {db_version_short}\n"
            f"📏 Размер БД: {db_size}\n\n"
            f"📈 *Активность:*\n"
            f"⏰ Последний анализ: {format_datetime(last_analysis) if last_analysis else 'Нет данных'}\n"
            f"🕐 Время сервера: {format_datetime(datetime.now())}",
            reply_markup=get_back_button("back_to_settings"),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error getting system info: {e}")

        await callback.message.edit_text(
            f"ℹ️ *Системная информация*\n\n"
            f"❌ Ошибка получения данных: {str(e)}\n\n"
            f"🤖 *Базовая информация:*\n"
            f"🐍 Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
            f"💻 Платформа: {platform.system()}\n"
            f"🕐 Время: {format_datetime(datetime.now())}",
            reply_markup=get_back_button("back_to_settings"),
            parse_mode="Markdown"
        )

    await callback.answer()


# === НАСТРОЙКИ УВЕДОМЛЕНИЙ ===
@settings_router.callback_query(F.data == "notification_settings")
async def notification_settings(callback: CallbackQuery):
    """Настройки уведомлений (заглушка для будущего функционала)"""
    await callback.message.edit_text(
        "🔔 *Настройки уведомлений*\n\n"
        "🔧 Функция в разработке.\n\n"
        "В следующих версиях будут доступны:\n"
        "• Уведомления о низких квотах\n"
        "• Ежедневные отчеты\n"
        "• Уведомления о новых мастерах\n"
        "• Алерты об ошибках системы\n"
        "• Еженедельная статистика",
        reply_markup=get_back_button("back_to_settings"),
        parse_mode="Markdown"
    )
    await callback.answer()


# === ЭКСПОРТ ДАННЫХ ===
@settings_router.callback_query(F.data == "export_data")
async def export_data_info(callback: CallbackQuery):
    """Информация об экспорте данных"""
    await callback.message.edit_text(
        "📤 *Экспорт данных*\n\n"
        "🔧 Функция в разработке.\n\n"
        "Планируемые возможности экспорта:\n"
        "• Список салонов (CSV/Excel)\n"
        "• Список мастеров (CSV/Excel)\n"
        "• Статистика анализов (CSV/Excel)\n"
        "• Отчеты по периодам\n"
        "• Полный дамп данных\n\n"
        "💡 Пока можете использовать SQL-запросы к базе данных для получения необходимых данных.",
        reply_markup=get_back_button("back_to_settings"),
        parse_mode="Markdown"
    )
    await callback.answer()