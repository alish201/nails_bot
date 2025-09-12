from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from loguru import logger

from app.keyboards.admin_kb import *
from app.states.admin_states import AdminStates
from app.database.models import Salon, Master, Analysis
from app.utils.helpers import format_datetime

salon_router = Router()


# === УПРАВЛЕНИЕ САЛОНАМИ ===
@salon_router.message(F.text == "🏢 Управление салонами")
async def salons_menu(message: Message):
    """Меню управления салонами"""
    await message.answer(
        "🏢 *Управление салонами*\n\n"
        "Выберите действие:",
        reply_markup=get_salons_menu(),
        parse_mode="Markdown"
    )


@salon_router.callback_query(F.data == "back_to_salons")
async def back_to_salons_menu(callback: CallbackQuery):
    """Возврат к меню салонов"""
    await callback.message.edit_text(
        "🏢 *Управление салонами*\n\n"
        "Выберите действие:",
        reply_markup=get_salons_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


# === ДОБАВЛЕНИЕ САЛОНА ===
@salon_router.callback_query(F.data == "add_salon")
async def add_salon_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления салона"""
    await callback.message.edit_text(
        "➕ *Добавление нового салона*\n\n"
        "Введите название салона:",
        reply_markup=get_back_button("back_to_salons"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_salon_name)
    await callback.answer()


@salon_router.message(AdminStates.waiting_for_salon_name)
async def process_salon_name(message: Message, state: FSMContext):
    """Обработка названия салона"""
    salon_name = message.text.strip()

    if len(salon_name) < 2:
        await message.answer(
            "❌ Название салона должно содержать минимум 2 символа. Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(salon_name) > 100:
        await message.answer(
            "❌ Название салона слишком длинное (максимум 100 символов). Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(salon_name=salon_name)
    await message.answer(
        f"🏢 Название: {salon_name}\n\n"
        f"Теперь введите город:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_salon_city)


@salon_router.message(AdminStates.waiting_for_salon_city)
async def process_salon_city(message: Message, state: FSMContext):
    """Обработка города салона"""
    city = message.text.strip()

    if len(city) < 2:
        await message.answer(
            "❌ Название города должно содержать минимум 2 символа. Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(city) > 50:
        await message.answer(
            "❌ Название города слишком длинное (максимум 50 символов). Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(city=city)
    data = await state.get_data()

    await message.answer(
        f"🏢 Название: {data['salon_name']}\n"
        f"🏙️ Город: {city}\n\n"
        f"Введите количество анализов (квоту):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_salon_quota)


@salon_router.message(AdminStates.waiting_for_salon_quota)
async def process_salon_quota(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка квоты салона"""
    try:
        quota = int(message.text.strip())
        if quota < 0:
            raise ValueError("Negative quota")
        if quota > 999999:
            raise ValueError("Too large quota")
    except ValueError:
        await message.answer(
            "❌ Введите корректное число от 0 до 999999:",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()

    # Проверяем, не существует ли уже такой салон
    existing_salon = await db_session.scalar(
        select(Salon).where(
            Salon.name == data['salon_name'],
            Salon.city == data['city'],
            Salon.is_active == True
        )
    )

    if existing_salon:
        await message.answer(
            f"❌ Салон с таким названием уже существует в городе {data['city']}.\n"
            f"Введите другое название или отмените действие:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(AdminStates.waiting_for_salon_name)
        return

    # Создаем новый салон
    new_salon = Salon(
        name=data['salon_name'],
        city=data['city'],
        quota_limit=quota
    )

    db_session.add(new_salon)
    await db_session.commit()
    await db_session.refresh(new_salon)

    await state.clear()
    await message.answer(
        f"✅ Салон успешно добавлен!\n\n"
        f"🏢 Название: {new_salon.name}\n"
        f"🏙️ Город: {new_salon.city}\n"
        f"💰 Квота: {new_salon.quota_limit}\n"
        f"📅 Создан: {format_datetime(new_salon.created_at)}",
        reply_markup=get_admin_main_menu()
    )

    logger.info(f"New salon created: {new_salon.name} in {new_salon.city} with quota {new_salon.quota_limit}")


# === СПИСОК САЛОНОВ ===
@salon_router.callback_query(F.data == "list_salons")
async def list_salons(callback: CallbackQuery, db_session: AsyncSession):
    """Список всех салонов"""
    query = select(Salon).where(Salon.is_active == True).order_by(Salon.name)
    result = await db_session.execute(query)
    salons = result.scalars().all()

    if not salons:
        await callback.message.edit_text(
            "📋 *Список салонов*\n\n"
            "Салоны не найдены.\n"
            "Добавьте первый салон, чтобы начать работу.",
            reply_markup=get_back_button("back_to_salons"),
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
        for salon in salons
    ]

    await callback.message.edit_text(
        f"📋 *Список салонов* ({len(salons)})\n\n"
        "Выберите салон для просмотра детальной информации:",
        reply_markup=get_salon_list_keyboard(salons_data),
        parse_mode="Markdown"
    )
    await callback.answer()


# === ДЕТАЛИ САЛОНА ===
@salon_router.callback_query(F.data.startswith("salon_"))
async def show_salon_details(callback: CallbackQuery, db_session: AsyncSession):
    """Показать детали салона"""
    salon_id = int(callback.data.split("_")[1])

    query = select(Salon).where(Salon.id == salon_id, Salon.is_active == True)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден", show_alert=True)
        return

    # Считаем количество мастеров
    masters_count = await db_session.scalar(
        select(func.count(Master.id)).where(
            Master.salon_id == salon_id,
            Master.is_active == True
        )
    )

    # Считаем количество анализов
    analyses_count = await db_session.scalar(
        select(func.count(Analysis.id)).where(Analysis.salon_id == salon_id)
    )

    quota_percentage = (salon.quota_used / salon.quota_limit * 100) if salon.quota_limit > 0 else 0
    status_icon = "🟢" if quota_percentage < 80 else "🟡" if quota_percentage < 95 else "🔴"

    await callback.message.edit_text(
        f"{status_icon} *{salon.name}*\n\n"
        f"🏙️ Город: {salon.city}\n"
        f"👤 Активных мастеров: {masters_count}\n"
        f"📸 Всего анализов: {analyses_count}\n\n"
        f"💰 *Квоты:*\n"
        f"📊 Использовано: {salon.quota_used}/{salon.quota_limit}\n"
        f"⏳ Осталось: {salon.quota_remaining}\n"
        f"📈 Процент использования: {quota_percentage:.1f}%\n\n"
        f"📅 Создан: {format_datetime(salon.created_at)}\n"
        f"🔄 Обновлен: {format_datetime(salon.updated_at)}\n\n"
        f"Выберите действие:",
        reply_markup=get_salon_actions_keyboard(salon_id),
        parse_mode="Markdown"
    )
    await callback.answer()


# === РЕДАКТИРОВАНИЕ САЛОНА ===
@salon_router.callback_query(F.data.startswith("edit_salon_"))
async def edit_salon_menu(callback: CallbackQuery, db_session: AsyncSession):
    """Меню редактирования салона"""
    salon_id = int(callback.data.split("_")[2])

    query = select(Salon).where(Salon.id == salon_id, Salon.is_active == True)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"✏️ *Редактирование салона*\n\n"
        f"🏢 Название: {salon.name}\n"
        f"🏙️ Город: {salon.city}\n"
        f"💰 Квота: {salon.quota_limit}\n\n"
        f"Что хотите изменить?",
        reply_markup=get_salon_edit_keyboard(salon_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@salon_router.callback_query(F.data.startswith("edit_salon_name_"))
async def edit_salon_name(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Редактирование названия салона"""
    salon_id = int(callback.data.split("_")[3])

    # Получаем текущие данные салона
    query = select(Salon).where(Salon.id == salon_id, Salon.is_active == True)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден", show_alert=True)
        return

    await state.update_data(salon_id=salon_id, current_name=salon.name)

    await callback.message.edit_text(
        f"✏️ *Редактирование названия салона*\n\n"
        f"Текущее название: {salon.name}\n\n"
        f"Введите новое название:",
        reply_markup=get_back_button(f"edit_salon_{salon_id}"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_salon_new_name)
    await callback.answer()


@salon_router.message(AdminStates.waiting_for_salon_new_name)
async def process_salon_new_name(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка нового названия салона"""
    new_name = message.text.strip()

    if len(new_name) < 2:
        await message.answer(
            "❌ Название должно содержать минимум 2 символа:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(new_name) > 100:
        await message.answer(
            "❌ Название слишком длинное (максимум 100 символов):",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()
    salon_id = data['salon_id']
    current_name = data['current_name']

    # Если название не изменилось
    if new_name == current_name:
        await message.answer(
            "ℹ️ Название не изменилось.",
            reply_markup=get_admin_main_menu()
        )
        await state.clear()
        return

    query = select(Salon).where(Salon.id == salon_id)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await message.answer("❌ Салон не найден")
        await state.clear()
        return

    # Проверяем уникальность в том же городе
    existing_salon = await db_session.scalar(
        select(Salon).where(
            Salon.name == new_name,
            Salon.city == salon.city,
            Salon.id != salon_id,
            Salon.is_active == True
        )
    )

    if existing_salon:
        await message.answer(
            f"❌ Салон с названием '{new_name}' уже существует в городе {salon.city}:",
            reply_markup=get_cancel_keyboard()
        )
        return

    old_name = salon.name
    salon.name = new_name

    await db_session.commit()
    await state.clear()

    await message.answer(
        f"✅ Название салона изменено!\n\n"
        f"Было: {old_name}\n"
        f"Стало: {new_name}",
        reply_markup=get_admin_main_menu()
    )

    logger.info(f"Salon name changed from '{old_name}' to '{new_name}' (ID: {salon_id})")


@salon_router.callback_query(F.data.startswith("edit_salon_city_"))
async def edit_salon_city(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Редактирование города салона"""
    salon_id = int(callback.data.split("_")[3])

    query = select(Salon).where(Salon.id == salon_id)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден", show_alert=True)
        return

    await state.update_data(salon_id=salon_id, current_city=salon.city)

    await callback.message.edit_text(
        f"✏️ *Редактирование города салона*\n\n"
        f"Текущий город: {salon.city}\n\n"
        f"Введите новый город:",
        reply_markup=get_back_button(f"edit_salon_{salon_id}"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_salon_new_city)
    await callback.answer()


@salon_router.message(AdminStates.waiting_for_salon_new_city)
async def process_salon_new_city(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка нового города салона"""
    new_city = message.text.strip()

    if len(new_city) < 2:
        await message.answer(
            "❌ Название города должно содержать минимум 2 символа:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(new_city) > 50:
        await message.answer(
            "❌ Название города слишком длинное (максимум 50 символов):",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()
    salon_id = data['salon_id']
    current_city = data['current_city']

    if new_city == current_city:
        await message.answer(
            "ℹ️ Город не изменился.",
            reply_markup=get_admin_main_menu()
        )
        await state.clear()
        return

    query = select(Salon).where(Salon.id == salon_id)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await message.answer("❌ Салон не найден")
        await state.clear()
        return

    # Проверяем уникальность с новым городом
    existing_salon = await db_session.scalar(
        select(Salon).where(
            Salon.name == salon.name,
            Salon.city == new_city,
            Salon.id != salon_id,
            Salon.is_active == True
        )
    )

    if existing_salon:
        await message.answer(
            f"❌ Салон с названием '{salon.name}' уже существует в городе {new_city}:",
            reply_markup=get_cancel_keyboard()
        )
        return

    old_city = salon.city
    salon.city = new_city

    await db_session.commit()
    await state.clear()

    await message.answer(
        f"✅ Город салона изменен!\n\n"
        f"Было: {old_city}\n"
        f"Стало: {new_city}",
        reply_markup=get_admin_main_menu()
    )

    logger.info(f"Salon city changed from '{old_city}' to '{new_city}' (ID: {salon_id})")


@salon_router.callback_query(F.data.startswith("edit_salon_quota_"))
async def edit_salon_quota(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Редактирование квоты салона"""
    salon_id = int(callback.data.split("_")[3])

    query = select(Salon).where(Salon.id == salon_id)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден", show_alert=True)
        return

    await state.update_data(salon_id=salon_id)

    await callback.message.edit_text(
        f"✏️ *Редактирование квот салона*\n\n"
        f"🏢 Салон: {salon.name}\n"
        f"📊 Текущий лимит: {salon.quota_limit}\n"
        f"✅ Использовано: {salon.quota_used}\n"
        f"⏳ Доступно: {salon.quota_remaining}\n\n"
        f"⚠️ *Внимание:* Установка лимита ниже использованных квот может привести к блокировке анализов.\n\n"
        f"Введите новый лимит квот:",
        reply_markup=get_back_button(f"edit_salon_{salon_id}"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_salon_new_quota)
    await callback.answer()


@salon_router.message(AdminStates.waiting_for_salon_new_quota)
async def process_salon_new_quota(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка новой квоты салона"""
    try:
        new_quota = int(message.text.strip())
        if new_quota < 0:
            raise ValueError("Negative quota")
        if new_quota > 999999:
            raise ValueError("Too large quota")
    except ValueError:
        await message.answer(
            "❌ Введите корректное число от 0 до 999999:",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()
    salon_id = data['salon_id']

    query = select(Salon).where(Salon.id == salon_id)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await message.answer("❌ Салон не найден")
        await state.clear()
        return

    old_quota = salon.quota_limit

    # Предупреждение, если новый лимит меньше использованных квот
    if new_quota < salon.quota_used:
        warning_text = (
            f"⚠️ *Предупреждение!*\n\n"
            f"Новый лимит ({new_quota}) меньше использованных квот ({salon.quota_used}).\n"
            f"Это заблокирует возможность проведения новых анализов в этом салоне.\n\n"
            f"Продолжить?"
        )
        # Здесь можно добавить подтверждение, но пока просто предупреждаем

    salon.quota_limit = new_quota

    await db_session.commit()
    await state.clear()

    status_icon = "🟢" if salon.quota_remaining > 0 else "🔴"

    await message.answer(
        f"✅ Квота салона изменена!\n\n"
        f"🏢 Салон: {salon.name}\n"
        f"📊 Было: {old_quota}\n"
        f"📈 Стало: {new_quota}\n"
        f"{status_icon} Доступно: {salon.quota_remaining}",
        reply_markup=get_admin_main_menu()
    )

    logger.info(f"Salon quota changed from {old_quota} to {new_quota} (ID: {salon_id})")


# === ПОПОЛНЕНИЕ КВОТ ===
@salon_router.message(F.text == "💰 Пополнить квоты")
async def quota_refill_menu(message: Message, db_session: AsyncSession):
    """Меню пополнения квот"""
    # Получаем список салонов
    query = select(Salon).where(Salon.is_active == True).order_by(Salon.name)
    result = await db_session.execute(query)
    salons = result.scalars().all()

    if not salons:
        await message.answer(
            "❌ Активные салоны не найдены.\n"
            "Сначала добавьте салоны для работы.",
            reply_markup=get_admin_main_menu()
        )
        return

    salons_data = [
        {
            'id': salon.id,
            'name': salon.name,
            'city': salon.city
        }
        for salon in salons
    ]

    await message.answer(
        "💰 *Пополнение квот*\n\n"
        "Выберите салон для пополнения квот:",
        reply_markup=get_salon_selection_keyboard(salons_data, "quota_salon"),
        parse_mode="Markdown"
    )


@salon_router.callback_query(F.data.startswith("quota_salon_"))
async def select_salon_for_quota(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Выбор салона для пополнения квот"""
    salon_id = int(callback.data.split("_")[-1])

    # Получаем информацию о салоне
    query = select(Salon).where(Salon.id == salon_id, Salon.is_active == True)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден", show_alert=True)
        return

    await state.update_data(salon_id=salon_id)

    quota_percentage = (salon.quota_used / salon.quota_limit * 100) if salon.quota_limit > 0 else 0
    status_icon = "🟢" if quota_percentage < 80 else "🟡" if quota_percentage < 95 else "🔴"

    await callback.message.edit_text(
        f"💰 *Пополнение квот*\n\n"
        f"{status_icon} *{salon.name}* ({salon.city})\n\n"
        f"📊 *Текущее состояние:*\n"
        f"💰 Лимит: {salon.quota_limit}\n"
        f"✅ Использовано: {salon.quota_used}\n"
        f"⏳ Доступно: {salon.quota_remaining}\n"
        f"📈 Использование: {quota_percentage:.1f}%\n\n"
        f"Введите количество анализов для добавления:",
        reply_markup=get_back_button("back_to_main"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_quota_amount)
    await callback.answer()


@salon_router.callback_query(F.data.startswith("add_quota_"))
async def add_quota_from_salon_details(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Пополнение квот из детальной информации о салоне"""
    salon_id = int(callback.data.split("_")[2])

    # Получаем информацию о салоне
    query = select(Salon).where(Salon.id == salon_id, Salon.is_active == True)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден", show_alert=True)
        return

    await state.update_data(salon_id=salon_id)

    quota_percentage = (salon.quota_used / salon.quota_limit * 100) if salon.quota_limit > 0 else 0
    status_icon = "🟢" if quota_percentage < 80 else "🟡" if quota_percentage < 95 else "🔴"

    await callback.message.edit_text(
        f"💰 *Пополнение квот*\n\n"
        f"{status_icon} *{salon.name}* ({salon.city})\n\n"
        f"📊 *Текущее состояние:*\n"
        f"💰 Лимит: {salon.quota_limit}\n"
        f"✅ Использовано: {salon.quota_used}\n"
        f"⏳ Доступно: {salon.quota_remaining}\n"
        f"📈 Использование: {quota_percentage:.1f}%\n\n"
        f"Введите количество анализов для добавления:",
        reply_markup=get_back_button(f"salon_{salon_id}"),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_quota_amount)
    await callback.answer()


@salon_router.message(AdminStates.waiting_for_quota_amount)
async def process_quota_amount(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка количества квот для пополнения"""
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError("Non-positive amount")
        if amount > 999999:
            raise ValueError("Too large amount")
    except ValueError:
        await message.answer(
            "❌ Введите положительное число от 1 до 999999:",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()
    salon_id = data['salon_id']

    # Обновляем квоты салона
    query = select(Salon).where(Salon.id == salon_id)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await message.answer(
            "❌ Салон не найден.",
            reply_markup=get_admin_main_menu()
        )
        await state.clear()
        return

    old_limit = salon.quota_limit
    new_limit = old_limit + amount

    # Проверяем, не превысим ли максимальный лимит
    if new_limit > 999999:
        await message.answer(
            f"❌ Превышен максимальный лимит квот (999999).\n"
            f"Максимально можно добавить: {999999 - old_limit}",
            reply_markup=get_cancel_keyboard()
        )
        return

    salon.quota_limit = new_limit

    await db_session.commit()
    await db_session.refresh(salon)

    await state.clear()

    await message.answer(
        f"✅ Квоты успешно пополнены!\n\n"
        f"🏢 Салон: {salon.name}\n"
        f"📊 Было: {old_limit}\n"
        f"➕ Добавлено: {amount}\n"
        f"📈 Стало: {salon.quota_limit}\n"
        f"💰 Доступно: {salon.quota_remaining}",
        reply_markup=get_admin_main_menu()
    )

    logger.info(f"Quota refilled for salon {salon.name}: +{amount} (total: {salon.quota_limit})")


# === УДАЛЕНИЕ САЛОНА ===
@salon_router.callback_query(F.data.startswith("delete_salon_"))
async def confirm_delete_salon(callback: CallbackQuery, db_session: AsyncSession):
    """Подтверждение удаления салона"""
    salon_id = int(callback.data.split("_")[2])

    query = select(Salon).where(Salon.id == salon_id, Salon.is_active == True)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден", show_alert=True)
        return

    # Считаем количество мастеров
    masters_count = await db_session.scalar(
        select(func.count(Master.id)).where(
            Master.salon_id == salon_id,
            Master.is_active == True
        )
    )

    # Считаем количество анализов
    analyses_count = await db_session.scalar(
        select(func.count(Analysis.id)).where(Analysis.salon_id == salon_id)
    )

    await callback.message.edit_text(
        f"🗑️ *Удаление салона*\n\n"
        f"🏢 Салон: {salon.name}\n"
        f"🏙️ Город: {salon.city}\n"
        f"👤 Активных мастеров: {masters_count}\n"
        f"📸 Всего анализов: {analyses_count}\n"
        f"💰 Квот использовано: {salon.quota_used}/{salon.quota_limit}\n\n"
        f"⚠️ **ВНИМАНИЕ!**\n"
        f"Это действие нельзя отменить!\n"
        f"• Салон будет деактивирован\n"
        f"• Все мастера салона будут деактивированы\n"
        f"• История анализов сохранится\n\n"
        f"Вы уверены?",
        reply_markup=get_confirmation_keyboard("delete_salon", salon_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@salon_router.callback_query(F.data.startswith("confirm_delete_salon_"))
async def delete_salon(callback: CallbackQuery, db_session: AsyncSession):
    """Удаление салона"""
    salon_id = int(callback.data.split("_")[3])

    query = select(Salon).where(Salon.id == salon_id)
    result = await db_session.execute(query)
    salon = result.scalar_one_or_none()

    if not salon:
        await callback.answer("❌ Салон не найден", show_alert=True)
        return

    salon_name = salon.name
    masters_deactivated = 0

    # Мягкое удаление - помечаем как неактивный
    salon.is_active = False

    # Также деактивируем всех мастеров этого салона
    masters_result = await db_session.execute(
        update(Master).where(
            Master.salon_id == salon_id,
            Master.is_active == True
        ).values(is_active=False).returning(Master.id)
    )
    masters_deactivated = len(masters_result.fetchall())

    await db_session.commit()

    await callback.message.edit_text(
        f"✅ Салон удален\n\n"
        f"🏢 {salon_name} успешно деактивирован\n"
        f"👤 Деактивировано мастеров: {masters_deactivated}\n\n"
        f"📊 История анализов сохранена в системе",
        reply_markup=get_back_button("list_salons")
    )

    logger.info(f"Salon deactivated: {salon_name} (ID: {salon_id}), masters deactivated: {masters_deactivated}")
    await callback.answer()


@salon_router.callback_query(F.data.startswith("cancel_delete_salon_"))
async def cancel_delete_salon(callback: CallbackQuery):
    """Отмена удаления салона"""
    salon_id = int(callback.data.split("_")[3])

    await callback.message.edit_text(
        "❌ Удаление отменено",
        reply_markup=get_back_button(f"salon_{salon_id}")
    )
    await callback.answer()