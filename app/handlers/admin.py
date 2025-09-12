from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.middlewares.auth import OwnerOnlyMiddleware
from app.keyboards.admin_kb import get_admin_main_menu, get_statistics_keyboard, get_back_button
from app.states.admin_states import AdminStates
from app.database.models import Owner, Salon, Master, Analysis, SystemLog
from app.utils.helpers import format_datetime, hash_password, verify_password
from config.settings import settings

# Импортируем модули с обработчиками
from .admin_salons import salon_router
from .admin_masters import master_router
from .admin_settings import settings_router

router = Router()
router.message.middleware(OwnerOnlyMiddleware())
router.callback_query.middleware(OwnerOnlyMiddleware())

# Подключаем дополнительные роутеры
router.include_router(salon_router)
router.include_router(master_router)
router.include_router(settings_router)


# === АВТОРИЗАЦИЯ ===
@router.message(AdminStates.waiting_for_password)
async def process_admin_password(message: Message, state: FSMContext, db_session: AsyncSession, owner):
    """Обработка пароля администратора"""
    password = message.text.strip()

    # Удаляем сообщение с паролем
    await message.delete()

    # Проверяем пароль
    if password == settings.ADMIN_PASSWORD:
        await state.clear()
        await message.answer(
            "✅ Авторизация успешна!\n\n"
            "Добро пожаловать в панель администратора:",
            reply_markup=get_admin_main_menu()
        )
        logger.info(f"Admin {message.from_user.id} successfully logged in")
    else:
        await message.answer(
            "❌ Неверный пароль. Попробуйте еще раз:",
            reply_markup=get_back_button("cancel_login")
        )
        logger.warning(f"Failed login attempt from {message.from_user.id}")


@router.callback_query(F.data == "cancel_login")
async def cancel_login(callback: CallbackQuery, state: FSMContext):
    """Отмена авторизации"""
    await state.clear()
    await callback.message.edit_text("❌ Авторизация отменена")
    await callback.answer()


# === СТАТИСТИКА ===
@router.message(F.text == "📊 Статистика")
async def statistics_menu(message: Message):
    """Меню статистики"""
    await message.answer(
        "📊 *Статистика системы*\n\n"
        "Выберите тип отчета:",
        reply_markup=get_statistics_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "stats_general")
async def general_statistics(callback: CallbackQuery, db_session: AsyncSession):
    """Общая статистика системы"""
    # Подсчитываем статистику
    salons_count = await db_session.scalar(
        select(func.count(Salon.id)).where(Salon.is_active == True)
    )
    masters_count = await db_session.scalar(
        select(func.count(Master.id)).where(Master.is_active == True)
    )
    analyses_count = await db_session.scalar(select(func.count(Analysis.id)))

    # Общая квота
    total_quota = await db_session.scalar(
        select(func.sum(Salon.quota_limit)).where(Salon.is_active == True)
    ) or 0
    used_quota = await db_session.scalar(
        select(func.sum(Salon.quota_used)).where(Salon.is_active == True)
    ) or 0

    remaining_quota = total_quota - used_quota
    quota_percentage = (used_quota / total_quota * 100) if total_quota > 0 else 0

    # Статистика за сегодня
    from datetime import datetime, date
    today = date.today()
    today_analyses = await db_session.scalar(
        select(func.count(Analysis.id)).where(
            func.date(Analysis.created_at) == today
        )
    )

    await callback.message.edit_text(
        f"📊 *Общая статистика системы*\n\n"
        f"🏢 Активных салонов: {salons_count}\n"
        f"👤 Активных мастеров: {masters_count}\n"
        f"📸 Всего анализов: {analyses_count}\n"
        f"📅 Анализов сегодня: {today_analyses}\n\n"
        f"💰 *Квоты:*\n"
        f"📊 Общий лимит: {total_quota}\n"
        f"✅ Использовано: {used_quota}\n"
        f"⏳ Осталось: {remaining_quota}\n"
        f"📈 Использование: {quota_percentage:.1f}%\n\n"
        f"🕐 Обновлено: {format_datetime(datetime.now())}",
        reply_markup=get_back_button("back_to_main"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_salons")
async def salons_statistics(callback: CallbackQuery, db_session: AsyncSession):
    """Статистика по салонам"""
    from sqlalchemy.orm import selectinload

    query = select(Salon).where(Salon.is_active == True).order_by(Salon.quota_used.desc())
    result = await db_session.execute(query)
    salons = result.scalars().all()

    if not salons:
        await callback.message.edit_text(
            "📊 *Статистика по салонам*\n\n"
            "Активные салоны не найдены.",
            reply_markup=get_back_button("back_to_main"),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    stats_text = "📊 *ТОП салонов по активности*\n\n"

    for i, salon in enumerate(salons[:10], 1):  # Топ-10
        masters_count = await db_session.scalar(
            select(func.count(Master.id)).where(
                Master.salon_id == salon.id,
                Master.is_active == True
            )
        )

        usage_percent = (salon.quota_used / salon.quota_limit * 100) if salon.quota_limit > 0 else 0
        status_icon = "🟢" if usage_percent < 80 else "🟡" if usage_percent < 95 else "🔴"

        stats_text += (
            f"{i}. {status_icon} *{salon.name}* ({salon.city})\n"
            f"   👤 Мастеров: {masters_count} | 📸 Анализов: {salon.quota_used}\n"
            f"   💰 Квоты: {salon.quota_used}/{salon.quota_limit} ({usage_percent:.1f}%)\n\n"
        )

    stats_text += f"📊 Показано: {min(len(salons), 10)} из {len(salons)} салонов"

    await callback.message.edit_text(
        stats_text,
        reply_markup=get_back_button("back_to_main"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_masters")
async def masters_statistics(callback: CallbackQuery, db_session: AsyncSession):
    """Статистика по мастерам"""
    from sqlalchemy.orm import selectinload

    query = select(Master).options(selectinload(Master.salon)).where(
        Master.is_active == True
    ).order_by(Master.analyses_count.desc())
    result = await db_session.execute(query)
    masters = result.scalars().all()

    if not masters:
        await callback.message.edit_text(
            "📊 *Статистика по мастерам*\n\n"
            "Активные мастера не найдены.",
            reply_markup=get_back_button("back_to_main"),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    stats_text = "📊 *ТОП мастеров по анализам*\n\n"

    total_analyses = sum(master.analyses_count for master in masters)

    for i, master in enumerate(masters[:15], 1):  # Топ-15
        salon_name = master.salon.name if master.salon else "Без салона"
        percent = (master.analyses_count / total_analyses * 100) if total_analyses > 0 else 0

        activity_icon = "🥇" if i <= 3 else "🥈" if i <= 8 else "🥉"

        stats_text += (
            f"{i}. {activity_icon} *{master.name}*\n"
            f"   🏢 {salon_name}\n"
            f"   📸 {master.analyses_count} анализов ({percent:.1f}%)\n\n"
        )

    stats_text += f"📊 Показано: {min(len(masters), 15)} из {len(masters)} мастеров"

    await callback.message.edit_text(
        stats_text,
        reply_markup=get_back_button("back_to_main"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_period")
async def period_statistics(callback: CallbackQuery, db_session: AsyncSession):
    """Статистика за период"""
    from datetime import datetime, timedelta

    now = datetime.now()
    today = now.date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Статистика за сегодня
    today_analyses = await db_session.scalar(
        select(func.count(Analysis.id)).where(
            func.date(Analysis.created_at) == today
        )
    )

    # Статистика за неделю
    week_analyses = await db_session.scalar(
        select(func.count(Analysis.id)).where(
            func.date(Analysis.created_at) >= week_ago
        )
    )

    # Статистика за месяц
    month_analyses = await db_session.scalar(
        select(func.count(Analysis.id)).where(
            func.date(Analysis.created_at) >= month_ago
        )
    )

    # Новые пользователи за неделю
    new_masters_week = await db_session.scalar(
        select(func.count(Master.id)).where(
            func.date(Master.created_at) >= week_ago
        )
    )

    # Средняя активность
    avg_daily = week_analyses / 7 if week_analyses > 0 else 0

    await callback.message.edit_text(
        f"📈 *Статистика за период*\n\n"
        f"📅 *Сегодня:*\n"
        f"📸 Анализов: {today_analyses}\n\n"
        f"📅 *За 7 дней:*\n"
        f"📸 Анализов: {week_analyses}\n"
        f"👤 Новых мастеров: {new_masters_week}\n"
        f"📊 В среднем в день: {avg_daily:.1f}\n\n"
        f"📅 *За 30 дней:*\n"
        f"📸 Анализов: {month_analyses}\n\n"
        f"🕐 Обновлено: {format_datetime(now)}",
        reply_markup=get_back_button("back_to_main"),
        parse_mode="Markdown"
    )
    await callback.answer()


# === ВОЗВРАТ В ГЛАВНОЕ МЕНЮ ===
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(
        "🏠 Главное меню администратора:",
        reply_markup=get_admin_main_menu()
    )
    await callback.answer()


# === ОБРАБОТКА ОТМЕНЫ ===
@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=get_admin_main_menu()
    )


# === СИСТЕМНАЯ ИНФОРМАЦИЯ ===
@router.callback_query(F.data == "system_info")
async def system_info(callback: CallbackQuery, db_session: AsyncSession):
    """Системная информация"""
    from datetime import datetime
    import sys
    import platform

    # Получаем информацию о системе
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Получаем последнюю активность
    last_analysis = await db_session.scalar(
        select(Analysis.created_at).order_by(Analysis.created_at.desc()).limit(1)
    )

    # Получаем количество записей в логах
    logs_count = await db_session.scalar(select(func.count(SystemLog.id)))

    await callback.message.edit_text(
        f"ℹ️ *Системная информация*\n\n"
        f"🤖 *Бот:*\n"
        f"📊 Версия: 1.0.0\n"
        f"🐍 Python: {python_version}\n"
        f"💻 Платформа: {platform.system()}\n\n"
        f"📈 *Активность:*\n"
        f"📝 Записей в логах: {logs_count}\n"
        f"⏰ Последний анализ: {format_datetime(last_analysis) if last_analysis else 'Нет данных'}\n\n"
        f"🕐 Время сервера: {format_datetime(datetime.now())}",
        reply_markup=get_back_button("back_to_main"),
        parse_mode="Markdown"
    )
    await callback.answer()