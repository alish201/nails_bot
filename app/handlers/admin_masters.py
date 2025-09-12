from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from loguru import logger

from app.keyboards.admin_kb import *
from app.states.admin_states import AdminStates
from app.database.models import Salon, Master, Analysis
from app.utils.helpers import format_datetime, validate_telegram_username

master_router = Router()


# === УПРАВЛЕНИЕ МАСТЕРАМИ ===
@master_router.message(F.text == "👤 Управление мастерами")
async def masters_menu(message: Message):
    """Меню управления мастерами"""
    await message.answer(
        "👤 *Управление мастерами*\n\n"
        "Выберите действие:",
        reply_markup=get_masters_menu(),
        parse_mode="Markdown"
    )


@master_router.callback_query(F.data == "back_to_masters")
async def back_to_masters_menu(callback: CallbackQuery):
    """Возврат к меню мастеров"""
    await callback.message.edit_text(
        "👤 *Управление мастерами*\n\n"
        "Выберите действие:",
        reply_markup=get_masters_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


# === ДОБАВЛЕНИЕ МАСТЕРА ===
@master_router.callback_query(F.data == "add_master")
async def add_master_start(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Начало добавления мастера"""
    # Проверяем наличие активных салонов
    salons_count = await db_session.scalar(
        select(func.count(Salon.id)).where(Salon.is_active == True)
    )

    if salons_count == 0:
        await callback.message.edit_text(
            "❌ *Нет доступных салонов*\n\n"
            "Сначала добавьте хотя бы один салон, чтобы создать мастера.",
            reply_markup=get_back_button("back_to_masters"),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "➕ *Добавление нового мастера*\n\n"
        "📝 Введите полное имя мастера:",
        reply_markup=get_back_button("back_to_masters"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_master_name)


@master_router.message(AdminStates.waiting_for_master_telegram)
async def process_master_telegram(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка Telegram ID мастера"""
    telegram_input = message.text.strip()

    # Проверяем, что введен числовой ID
    try:
        telegram_id = int(telegram_input)
    except ValueError:
        await message.answer(
            "❌ Telegram ID должен быть числом.\n\n"
            "Пример правильного ID: 123456789\n"
            "Введите корректный числовой ID:",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Проверяем валидность ID
    if telegram_id <= 0:
        await message.answer(
            "❌ Telegram ID должен быть положительным числом:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if telegram_id < 10000:
        await message.answer(
            "❌ Telegram ID слишком короткий. Убедитесь, что используете правильный ID:",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Проверяем, что мастер с таким ID не существует
    existing_master = await db_session.scalar(
        select(Master).where(Master.telegram_id == telegram_id, Master.is_active == True)
    )
    if existing_master:
        await message.answer(
            f"❌ Мастер с Telegram ID {telegram_id} уже существует в системе.\n"
            f"Имя: {existing_master.name}\n\n"
            f"Введите другой ID:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(telegram_id=telegram_id)

    # Получаем список активных салонов для выбора
    query = select(Salon).where(Salon.is_active == True).order_by(Salon.name, Salon.city)
    result = await db_session.execute(query)
    salons = result.scalars().all()

    if not salons:
        await message.answer(
            "❌ Нет активных салонов для привязки мастера.",
            reply_markup=get_admin_main_menu()
        )
        await state.clear()
        return

    salons_data = [
        {
            'id': salon.id,
            'name': salon.name,
            'city': salon.city
        }
        for salon in salons
    ]

    data = await state.get_data()

    await message.answer(
        f"👤 Имя: *{data['master_name']}*\n"
        f"💬 Telegram ID: `{telegram_id}`\n\n"
        f"🏢 Выберите салон для мастера:",
        reply_markup=get_salon_selection_keyboard(salons_data, "select_salon_for_master"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_master_salon)

@master_router.callback_query(F.data.startswith("select_salon_for_master_"))
async def process_master_salon(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Обработка выбора салона для мастера"""
    salon_id = int(callback.data.split("_")[-1])

    # Получаем данные мастера из состояния
    data = await state.get_data()

    # Получаем информацию о выбранном салоне
    query = select(Salon).where(Salon.id == salon_id, Salon.is_active == True)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден или неактивен", show_alert=True)
        return

    # Создаем нового мастера
    new_master = Master(
        name=data['master_name'],
        telegram_id=data['telegram_id'],
        salon_id=salon_id
    )

    try:
        db_session.add(new_master)
        await db_session.commit()
        await db_session.refresh(new_master)

        await state.clear()

        await callback.message.edit_text(
            f"✅ Мастер успешно добавлен!\n\n"
            f"👤 Имя: {new_master.name}\n"
            f"💬 Telegram ID: {data['telegram_id']}\n"
            f"🏢 Салон: {salon.name} ({salon.city})\n"
            f"📅 Создан: {format_datetime(new_master.created_at)}\n\n"
            f"ℹ️ Мастер может начать использовать бота командой /start",
            reply_markup=get_back_button("back_to_masters")
        )

        logger.info(f"New master created: {new_master.name} (ID: {new_master.telegram_id}) for salon {salon.name}")
        await callback.answer("Мастер создан!")

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Error creating master: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при создании мастера. Попробуйте еще раз.",
            reply_markup=get_back_button("back_to_masters")
        )
        await callback.answer()


# === СПИСОК МАСТЕРОВ ===
@master_router.callback_query(F.data == "list_masters")
async def list_masters(callback: CallbackQuery, db_session: AsyncSession):
    """Список всех мастеров"""
    query = select(Master).options(selectinload(Master.salon)).where(
        Master.is_active == True
    ).order_by(Master.name)
    result = await db_session.execute(query)
    masters = result.scalars().all()

    if not masters:
        await callback.message.edit_text(
            "📋 *Список мастеров*\n\n"
            "Мастера не найдены.\n"
            "Добавьте первого мастера, чтобы начать работу.",
            reply_markup=get_back_button("back_to_masters"),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    masters_data = [
        {
            'id': master.id,
            'name': master.name,
            'salon_name': master.salon.name if master.salon else "Салон удален"
        }
        for master in masters
    ]

    await callback.message.edit_text(
        f"📋 *Список мастеров* ({len(masters)})\n\n"
        "Выберите мастера для просмотра детальной информации:",
        reply_markup=get_master_list_keyboard(masters_data),
        parse_mode="Markdown"
    )
    await callback.answer()


# === ДЕТАЛИ МАСТЕРА ===
@master_router.callback_query(F.data.startswith("master_"))
async def show_master_details(callback: CallbackQuery, db_session: AsyncSession):
    """Показать детали мастера"""
    master_id = int(callback.data.split("_")[1])

    query = select(Master).options(selectinload(Master.salon)).where(
        Master.id == master_id, Master.is_active == True
    )
    result = await db_session.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return

    salon_info = f"{master.salon.name} ({master.salon.city})" if master.salon else "❌ Салон не найден"

    # Получаем статистику мастера
    analyses_today = await db_session.scalar(
        select(func.count(Analysis.id)).where(
            Analysis.master_id == master_id,
            func.date(Analysis.created_at) == func.current_date()
        )
    )

    # Статус активности
    if master.salon and master.salon.is_active:
        quota_remaining = master.salon.quota_remaining
        status_icon = "🟢" if quota_remaining > 10 else "🟡" if quota_remaining > 0 else "🔴"
        quota_info = f"{status_icon} Доступно анализов: {quota_remaining}"
    else:
        quota_info = "🔴 Салон неактивен"

    await callback.message.edit_text(
        f"👤 *{master.name}*\n\n"
        f"💬 Telegram ID: `{master.telegram_id}`\n"
        f"🏢 Салон: {salon_info}\n"
        f"{quota_info}\n\n"
        f"📊 *Статистика:*\n"
        f"📸 Всего анализов: {master.analyses_count}\n"
        f"📅 Анализов сегодня: {analyses_today}\n\n"
        f"📅 Добавлен: {format_datetime(master.created_at)}\n"
        f"🔄 Обновлен: {format_datetime(master.updated_at)}\n\n"
        f"Выберите действие:",
        reply_markup=get_master_actions_keyboard(master_id),
        parse_mode="Markdown"
    )
    await callback.answer()


# === РЕДАКТИРОВАНИЕ МАСТЕРА ===
@master_router.callback_query(F.data.startswith("edit_master_"))
async def edit_master_menu(callback: CallbackQuery, db_session: AsyncSession):
    """Меню редактирования мастера"""
    master_id = int(callback.data.split("_")[2])

    query = select(Master).options(selectinload(Master.salon)).where(
        Master.id == master_id, Master.is_active == True
    )
    result = await db_session.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return

    salon_info = f"{master.salon.name} ({master.salon.city})" if master.salon else "❌ Салон не найден"

    await callback.message.edit_text(
        f"✏️ *Редактирование мастера*\n\n"
        f"👤 Имя: {master.name}\n"
        f"💬 Telegram ID: {master.telegram_id}\n"
        f"🏢 Салон: {salon_info}\n\n"
        f"Что хотите изменить?",
        reply_markup=get_master_edit_keyboard(master_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@master_router.callback_query(F.data.startswith("edit_master_name_"))
async def edit_master_name(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Редактирование имени мастера"""
    master_id = int(callback.data.split("_")[3])

    query = select(Master).where(Master.id == master_id, Master.is_active == True)
    result = await db_session.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return

    await state.update_data(master_id=master_id, current_name=master.name)

    await callback.message.edit_text(
        f"✏️ *Редактирование имени мастера*\n\n"
        f"Текущее имя: {master.name}\n\n"
        f"Введите новое имя:",
        reply_markup=get_back_button(f"edit_master_{master_id}"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_master_new_name)
    await callback.answer()


@master_router.message(AdminStates.waiting_for_master_new_name)
async def process_master_new_name(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка нового имени мастера"""
    new_name = message.text.strip()

    if len(new_name) < 2:
        await message.answer(
            "❌ Имя должно содержать минимум 2 символа:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(new_name) > 100:
        await message.answer(
            "❌ Имя слишком длинное (максимум 100 символов):",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()
    master_id = data['master_id']
    current_name = data['current_name']

    if new_name == current_name:
        await message.answer(
            "ℹ️ Имя не изменилось.",
            reply_markup=get_admin_main_menu()
        )
        await state.clear()
        return

    query = select(Master).where(Master.id == master_id)
    result = await db_session.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        await message.answer("❌ Мастер не найден")
        await state.clear()
        return

    old_name = master.name
    master.name = new_name

    await db_session.commit()
    await state.clear()

    await message.answer(
        f"✅ Имя мастера изменено!\n\n"
        f"Было: {old_name}\n"
        f"Стало: {new_name}",
        reply_markup=get_admin_main_menu()
    )

    logger.info(f"Master name changed from '{old_name}' to '{new_name}' (ID: {master_id})")


@master_router.callback_query(F.data.startswith("edit_master_telegram_"))
async def edit_master_telegram(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Редактирование Telegram ID мастера"""
    master_id = int(callback.data.split("_")[3])

    query = select(Master).where(Master.id == master_id, Master.is_active == True)
    result = await db_session.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return

    await state.update_data(master_id=master_id, current_telegram_id=master.telegram_id)

    await callback.message.edit_text(
        f"✏️ *Редактирование Telegram ID*\n\n"
        f"Текущий ID: `{master.telegram_id}`\n\n"
        f"⚠️ *Внимание:* После изменения ID мастер потеряет доступ к боту по старому ID.\n\n"
        f"Введите новый Telegram ID:",
        reply_markup=get_back_button(f"edit_master_{master_id}"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_master_new_telegram)
    await callback.answer()


@master_router.message(AdminStates.waiting_for_master_new_telegram)
async def process_master_new_telegram(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка нового Telegram ID мастера"""
    try:
        new_telegram_id = int(message.text.strip())
        if new_telegram_id <= 0:
            raise ValueError("Non-positive ID")
        if new_telegram_id < 10000:
            raise ValueError("Too short ID")
    except ValueError:
        await message.answer(
            "❌ Введите корректный положительный Telegram ID (минимум 5 цифр):",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()
    master_id = data['master_id']
    current_telegram_id = data['current_telegram_id']

    if new_telegram_id == current_telegram_id:
        await message.answer(
            "ℹ️ Telegram ID не изменился.",
            reply_markup=get_admin_main_menu()
        )
        await state.clear()
        return

    # Проверяем, не занят ли этот ID другим мастером
    existing_master = await db_session.scalar(
        select(Master).where(
            Master.telegram_id == new_telegram_id,
            Master.id != master_id,
            Master.is_active == True
        )
    )
    if existing_master:
        await message.answer(
            f"❌ Telegram ID {new_telegram_id} уже используется мастером:\n"
            f"Имя: {existing_master.name}\n\n"
            f"Введите другой ID:",
            reply_markup=get_cancel_keyboard()
        )
        return

    query = select(Master).where(Master.id == master_id)
    result = await db_session.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        await message.answer("❌ Мастер не найден")
        await state.clear()
        return

    old_telegram_id = master.telegram_id
    master.telegram_id = new_telegram_id

    await db_session.commit()
    await state.clear()

    await message.answer(
        f"✅ Telegram ID мастера изменен!\n\n"
        f"👤 Мастер: {master.name}\n"
        f"Было: {old_telegram_id}\n"
        f"Стало: {new_telegram_id}\n\n"
        f"ℹ️ Мастер должен перезапустить бота командой /start",
        reply_markup=get_admin_main_menu()
    )

    logger.info(f"Master telegram_id changed from {old_telegram_id} to {new_telegram_id} (ID: {master_id})")


# === СМЕНА САЛОНА МАСТЕРА ===
@master_router.callback_query(F.data.startswith("change_salon_"))
async def change_master_salon(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Смена салона мастера"""
    master_id = int(callback.data.split("_")[2])

    # Получаем информацию о мастере
    master_query = select(Master).options(selectinload(Master.salon)).where(
        Master.id == master_id, Master.is_active == True
    )
    master_result = await db_session.execute(master_query)
    master = master_result.scalar_one_or_none()

    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return

    # Получаем список активных салонов
    query = select(Salon).where(Salon.is_active == True).order_by(Salon.name, Salon.city)
    result = await db_session.execute(query)
    salons = result.scalars().all()

    if not salons:
        await callback.message.edit_text(
            "❌ Нет доступных активных салонов для перевода мастера.",
            reply_markup=get_back_button(f"master_{master_id}"),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    # Убираем текущий салон из списка, если он есть
    available_salons = [salon for salon in salons if salon.id != master.salon_id]

    if not available_salons:
        await callback.message.edit_text(
            "❌ Нет других доступных салонов для перевода мастера.",
            reply_markup=get_back_button(f"master_{master_id}"),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    salons_data = [
        {
            'id': salon.id,
            'name': salon.name,
            'city': salon.city
        }
        for salon in available_salons
    ]

    current_salon = f"{master.salon.name} ({master.salon.city})" if master.salon else "Не указан"

    await state.update_data(master_id=master_id)

    await callback.message.edit_text(
        f"🔄 *Смена салона мастера*\n\n"
        f"👤 Мастер: {master.name}\n"
        f"🏢 Текущий салон: {current_salon}\n\n"
        f"Выберите новый салон:",
        reply_markup=get_salon_selection_keyboard(salons_data, "new_salon_for_master"),
        parse_mode="Markdown"
    )
    await callback.answer()


@master_router.callback_query(F.data.startswith("new_salon_for_master_"))
async def process_new_salon_for_master(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Обработка нового салона для мастера"""
    salon_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    master_id = data['master_id']

    # Получаем мастера с текущим салоном
    master_query = select(Master).options(selectinload(Master.salon)).where(Master.id == master_id)
    master_result = await db_session.execute(master_query)
    master = master_result.scalar_one_or_none()

    # Получаем новый салон
    salon_query = select(Salon).where(Salon.id == salon_id, Salon.is_active == True)
    salon_result = await db_session.execute(salon_query)
    new_salon = salon_result.scalar_one_or_none()

    if not master or not new_salon:
        await callback.answer("❌ Мастер или салон не найдены", show_alert=True)
        await state.clear()
        return

    old_salon = master.salon
    old_salon_info = f"{old_salon.name} ({old_salon.city})" if old_salon else "Не указан"

    # Обновляем салон мастера
    master.salon_id = salon_id

    await db_session.commit()
    await state.clear()

    await callback.message.edit_text(
        f"✅ Салон мастера изменен!\n\n"
        f"👤 Мастер: {master.name}\n"
        f"🔄 Было: {old_salon_info}\n"
        f"✅ Стало: {new_salon.name} ({new_salon.city})\n\n"
        f"ℹ️ Мастер может проверить изменения командой /start",
        reply_markup=get_back_button("list_masters")
    )

    logger.info(f"Master {master.name} moved from salon {old_salon_info} to {new_salon.name}")
    await callback.answer("Салон изменен!")


# === УДАЛЕНИЕ МАСТЕРА ===
@master_router.callback_query(F.data.startswith("delete_master_"))
async def confirm_delete_master(callback: CallbackQuery, db_session: AsyncSession):
    """Подтверждение удаления мастера"""
    master_id = int(callback.data.split("_")[2])

    query = select(Master).options(selectinload(Master.salon)).where(
        Master.id == master_id, Master.is_active == True
    )
    result = await db_session.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return

    salon_info = f"{master.salon.name} ({master.salon.city})" if master.salon else "❌ Салон удален"

    # Получаем количество анализов за последние 30 дней
    from datetime import datetime, timedelta
    month_ago = datetime.now() - timedelta(days=30)
    recent_analyses = await db_session.scalar(
        select(func.count(Analysis.id)).where(
            Analysis.master_id == master_id,
            Analysis.created_at >= month_ago
        )
    )

    await callback.message.edit_text(
        f"🗑️ *Удаление мастера*\n\n"
        f"👤 Мастер: {master.name}\n"
        f"💬 Telegram ID: {master.telegram_id}\n"
        f"🏢 Салон: {salon_info}\n\n"
        f"📊 *Статистика:*\n"
        f"📸 Всего анализов: {master.analyses_count}\n"
        f"📅 За последний месяц: {recent_analyses}\n"
        f"📅 В системе с: {format_datetime(master.created_at)}\n\n"
        f"⚠️ **ВНИМАНИЕ!**\n"
        f"Это действие нельзя отменить!\n"
        f"• Мастер будет деактивирован\n"
        f"• Доступ к боту будет заблокирован\n"
        f"• История анализов сохранится\n\n"
        f"Вы уверены?",
        reply_markup=get_confirmation_keyboard("delete_master", master_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@master_router.callback_query(F.data.startswith("confirm_delete_master_"))
async def delete_master(callback: CallbackQuery, db_session: AsyncSession):
    """Удаление мастера"""
    master_id = int(callback.data.split("_")[3])

    query = select(Master).where(Master.id == master_id)
    result = await db_session.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return

    master_name = master.name
    telegram_id = master.telegram_id
    analyses_count = master.analyses_count

    # Мягкое удаление - помечаем как неактивный
    master.is_active = False

    await db_session.commit()

    await callback.message.edit_text(
        f"✅ Мастер удален\n\n"
        f"👤 {master_name} (ID: {telegram_id}) успешно деактивирован\n"
        f"📊 Сохранено анализов: {analyses_count}\n\n"
        f"ℹ️ История работы мастера сохранена в системе",
        reply_markup=get_back_button("list_masters")
    )

    logger.info(f"Master deactivated: {master_name} (ID: {master_id}, Telegram: {telegram_id})")
    await callback.answer()


@master_router.callback_query(F.data.startswith("cancel_delete_master_"))
async def cancel_delete_master(callback: CallbackQuery):
    """Отмена удаления мастера"""
    master_id = int(callback.data.split("_")[3])

    await callback.message.edit_text(
        "❌ Удаление отменено",
        reply_markup=get_back_button(f"master_{master_id}")
    )
    await callback.answer()


@master_router.message(AdminStates.waiting_for_master_name)
async def process_master_name(message: Message, state: FSMContext):
    """Обработка имени мастера"""
    master_name = message.text.strip()

    if len(master_name) < 2:
        await message.answer(
            "❌ Имя мастера должно содержать минимум 2 символа. Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(master_name) > 100:
        await message.answer(
            "❌ Имя мастера слишком длинное (максимум 100 символов). Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Проверяем, что имя содержит только буквы, цифры, пробелы и основные символы
    allowed_chars = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZабвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ0123456789 .-'")
    if not all(char in allowed_chars for char in master_name):
        await message.answer(
            "❌ Имя содержит недопустимые символы. Используйте только буквы, цифры и основные символы:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(master_name=master_name)
    await message.answer(
        f"👤 Имя: *{master_name}*\n\n"
        f"💬 Теперь введите Telegram ID мастера.\n\n"
        f"ℹ️ *Как получить ID:*\n"
        f"• Мастер должен написать боту @userinfobot\n"
        f"• Скопировать числовой ID из ответа\n"
        f"• ID выглядит как: 123456789\n\n"
        f"Введите Telegram ID:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_master_telegram)