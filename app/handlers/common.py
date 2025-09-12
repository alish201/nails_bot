from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from app.keyboards.admin_kb import get_admin_main_menu
from app.keyboards.master_kb import get_master_main_menu
from app.states.admin_states import AdminStates
from app.database.models import Salon, Master, Analysis
from app.utils.helpers import format_user_info

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_session: AsyncSession, 
                   is_owner: bool, is_master: bool, owner=None, master=None):
    """Обработчик команды /start"""
    await state.clear()
    
    user_info = format_user_info(
        message.from_user.full_name,
        message.from_user.username,
        message.from_user.id
    )
    
    if is_owner:
        logger.info(f"Owner started bot: {user_info}")
        await message.answer(
            f"👋 Добро пожаловать, администратор!\n\n"
            f"🏢 Система управления салонами красоты\n"
            f"📊 Анализ фотографий волос с ИИ\n\n"
            f"Выберите действие:",
            reply_markup=get_admin_main_menu()
        )
    elif is_master:
        # Получаем информацию о салоне мастера с eager loading
        master_query = select(Master).options(selectinload(Master.salon)).where(
            Master.telegram_id == message.from_user.id,
            Master.is_active == True
        )
        result = await db_session.execute(master_query)
        master_with_salon = result.scalar_one_or_none()
        
        if master_with_salon and master_with_salon.salon:
            salon = master_with_salon.salon
            quota_remaining = salon.quota_limit - salon.quota_used
            
            logger.info(f"Master started bot: {user_info}")
            await message.answer(
                f"👋 Добро пожаловать, {master_with_salon.name}!\n\n"
                f"🏢 Салон: {salon.name}\n"
                f"🏙️ Город: {salon.city}\n"
                f"💰 Доступно анализов: {quota_remaining}\n\n"
                f"Выберите действие:",
                reply_markup=get_master_main_menu()
            )
        else:
            await message.answer(
                f"👋 Добро пожаловать!\n\n"
                f"❌ Ваш профиль мастера не настроен или салон не найден.\n"
                f"📞 Обратитесь к администратору.",
                reply_markup=get_master_main_menu()
            )
    else:
        logger.warning(f"Unauthorized user started bot: {user_info}")
        await message.answer(
            "❌ У вас нет доступа к этому боту.\n\n"
            "📞 Обратитесь к администратору для получения доступа."
        )


@router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext, is_owner: bool):
    """Обработчик команды /login для администраторов"""
    if is_owner:
        await message.answer(
            "✅ Вы уже авторизованы как администратор.",
            reply_markup=get_admin_main_menu()
        )
        return
    
    await message.answer(
        "🔐 Введите пароль администратора:",
        reply_markup=None
    )
    await state.set_state(AdminStates.waiting_for_password)


@router.message(Command("help"))
async def cmd_help(message: Message, is_owner: bool, is_master: bool):
    """Обработчик команды /help"""
    if is_owner:
        help_text = (
            "🤖 *Помощь для администратора*\n\n"
            "📋 *Доступные команды:*\n"
            "/start - Главное меню\n"
            "/help - Эта справка\n"
            "/stats - Быстрая статистика\n\n"
            "🏢 *Управление салонами:*\n"
            "• Добавление и редактирование салонов\n"
            "• Управление квотами анализов\n"
            "• Просмотр статистики по салонам\n\n"
            "👤 *Управление мастерами:*\n"
            "• Добавление мастеров\n"
            "• Привязка к салонам\n"
            "• Контроль активности\n\n"
            "📊 *Аналитика:*\n"
            "• Общая статистика системы\n"
            "• Детализация по салонам и мастерам\n"
            "• История анализов"
        )
    elif is_master:
        help_text = (
            "🤖 *Помощь для мастера*\n\n"
            "📋 *Доступные команды:*\n"
            "/start - Главное меню\n"
            "/help - Эта справка\n"
            "/quota - Остаток анализов\n\n"
            "📸 *Анализ фото:*\n"
            "• Отправка фотографий для анализа\n"
            "• Получение результатов ИИ\n"
            "• Контроль расхода квот\n\n"
            "📖 *Инструкции:*\n"
            "• Как правильно фотографировать\n"
            "• Что анализирует система\n"
            "• Частые вопросы и ответы\n\n"
            "📊 *Статистика:*\n"
            "• Количество проведенных анализов\n"
            "• История работы"
        )
    else:
        help_text = (
            "❌ *У вас нет доступа к этому боту*\n\n"
            "📞 Обратитесь к администратору салона для получения доступа.\n\n"
            "ℹ️ Этот бот предназначен для анализа фотографий волос с помощью ИИ."
        )
    
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("stats"))
async def cmd_stats(message: Message, db_session: AsyncSession, is_owner: bool, is_master: bool, master=None):
    """Быстрая статистика"""
    if is_owner:
        # Статистика для администратора
        from sqlalchemy import func
        
        # Подсчитываем общую статистику
        salons_count = await db_session.scalar(select(func.count(Salon.id)).where(Salon.is_active == True))
        masters_count = await db_session.scalar(select(func.count(Master.id)).where(Master.is_active == True))
        analyses_count = await db_session.scalar(select(func.count(Analysis.id)))
        
        await message.answer(
            f"📊 *Быстрая статистика:*\n\n"
            f"🏢 Активных салонов: {salons_count}\n"
            f"👤 Активных мастеров: {masters_count}\n"
            f"📸 Всего анализов: {analyses_count}",
            parse_mode="Markdown"
        )
    elif is_master and master:
        # Получаем мастера с салоном
        master_query = select(Master).options(selectinload(Master.salon)).where(
            Master.id == master.id
        )
        result = await db_session.execute(master_query)
        master_with_salon = result.scalar_one_or_none()
        
        if master_with_salon and master_with_salon.salon:
            salon = master_with_salon.salon
            quota_remaining = salon.quota_limit - salon.quota_used
            
            await message.answer(
                f"📊 *Ваша статистика:*\n\n"
                f"🏢 Салон: {salon.name}\n"
                f"📸 Проведено анализов: {master_with_salon.analyses_count}\n"
                f"💰 Доступно анализов: {quota_remaining}",
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Информация о салоне не найдена.")
    else:
        await message.answer("❌ У вас нет доступа к статистике.")


@router.message(Command("quota"))
async def cmd_quota(message: Message, db_session: AsyncSession, is_master: bool, master=None):
    """Проверка остатка квот для мастера"""
    if not is_master or not master:
        await message.answer("❌ Эта команда доступна только мастерам.")
        return
    
    # Получаем мастера с салоном
    master_query = select(Master).options(selectinload(Master.salon)).where(
        Master.id == master.id
    )
    result = await db_session.execute(master_query)
    master_with_salon = result.scalar_one_or_none()
    
    if master_with_salon and master_with_salon.salon:
        salon = master_with_salon.salon
        quota_remaining = salon.quota_limit - salon.quota_used
        quota_percentage = (salon.quota_used / salon.quota_limit * 100) if salon.quota_limit > 0 else 0
        
        status_emoji = "🟢" if quota_remaining > 10 else "🟡" if quota_remaining > 0 else "🔴"
        
        await message.answer(
            f"{status_emoji} *Остаток анализов:*\n\n"
            f"💰 Доступно: {quota_remaining}\n"
            f"📊 Использовано: {salon.quota_used}/{salon.quota_limit}\n"
            f"📈 Процент использования: {quota_percentage:.1f}%\n\n"
            f"🏢 Салон: {salon.name}",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Информация о салоне не найдена.")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext, is_owner: bool, is_master: bool):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.delete()
    
    if is_owner:
        await callback.message.answer(
            "🏠 Главное меню администратора:",
            reply_markup=get_admin_main_menu()
        )
    elif is_master:
        await callback.message.answer(
            "🏠 Главное меню мастера:",
            reply_markup=get_master_main_menu()
        )
    
    await callback.answer()


@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext, is_owner: bool, is_master: bool):
    """Отмена текущего действия"""
    await state.clear()
    
    if is_owner:
        await message.answer(
            "❌ Действие отменено.",
            reply_markup=get_admin_main_menu()
        )
    elif is_master:
        await message.answer(
            "❌ Действие отменено.",
            reply_markup=get_master_main_menu()
        )
    else:
        await message.answer("❌ Действие отменено.")
