from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PhotoSize
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from loguru import logger
from datetime import datetime
from typing import List

from app.middlewares.auth import MasterOnlyMiddleware
from app.keyboards.master_kb import *
from app.states.master_states import MasterStates
from app.database.models import Master, Salon, Analysis
from app.utils.helpers import format_datetime

router = Router()
router.message.middleware(MasterOnlyMiddleware())
router.callback_query.middleware(MasterOnlyMiddleware())


# === ГЛАВНОЕ МЕНЮ И НАВИГАЦИЯ ===
@router.message(F.text == "📖 Инструкция")
async def show_instruction(message: Message):
    """Показать инструкцию по использованию"""
    try:
        instruction_text = """📖 *Инструкция по использованию*

🔍 *Как провести анализ:*

1️⃣ **Начать анализ** 
   • Нажмите "📸 Начать анализ"
   • Проверьте остаток квот

2️⃣ **Фотографирование**
   • Сделайте фото первой руки
   • Сделайте фото второй руки
   • Можно добавить несколько фото каждой руки

3️⃣ **Опрос мастера**
   • Опишите состояние ногтей клиента
   • Укажите особенности и пожелания

4️⃣ **ИИ анализ**
   • Система автоматически проанализирует фото
   • Будет создан дневник роста ногтей

5️⃣ **Результаты**
   • Просмотрите результаты анализа
   • Примите или оспорьте результаты
   • Квота спишется только после принятия

💡 *Полезные советы:*
• Делайте качественные фото при хорошем освещении
• Подробно описывайте состояние ногтей в опросе
• Если результат не устраивает - можно оспорить
• Квота не списывается при отмене или споре

❓ *Есть вопросы?*
Обратитесь к администратору салона."""

        await message.answer(instruction_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in show_instruction: {e}")
        await message.answer("❌ Ошибка при загрузке инструкции")


@router.message(F.text == "📊 Моя статистика")
async def show_my_statistics(message: Message, master: Master, db_session: AsyncSession):
    """Показать статистику мастера"""
    try:
        # Получаем мастера с салоном
        master_query = select(Master).options(selectinload(Master.salon)).where(Master.id == master.id)
        result = await db_session.execute(master_query)
        master_with_salon = result.scalar_one_or_none()

        if not master_with_salon:
            await message.answer("❌ Информация о мастере не найдена.")
            return

        # Получаем статистику анализов мастера
        analysis_query = select(Analysis).where(Analysis.master_id == master.id)
        analyses_result = await db_session.execute(analysis_query)
        analyses = analyses_result.scalars().all()

        # Подсчитываем статистику
        total_analyses = len(analyses)
        completed_analyses = len([a for a in analyses if a.status == "completed"])
        disputed_analyses = len([a for a in analyses if a.status == "disputed"])
        in_progress = len([a for a in analyses if a.status in ["started", "ai_analyzing", "ready_for_ai"]])

        # Последний анализ
        last_analysis = None
        if analyses:
            last_analysis = max(analyses, key=lambda x: x.created_at if x.created_at else datetime.min)

        stats_text = f"📊 *Статистика мастера*\n\n"
        stats_text += f"👤 Мастер: {master_with_salon.name}\n"
        if master_with_salon.salon:
            stats_text += f"🏢 Салон: {master_with_salon.salon.name}\n"
            stats_text += f"🏙️ Город: {master_with_salon.salon.city}\n\n"

        stats_text += f"📈 *Общая статистика:*\n"
        stats_text += f"• Всего анализов: {total_analyses}\n"
        stats_text += f"• Завершенных: {completed_analyses}\n"
        stats_text += f"• В процессе: {in_progress}\n"
        stats_text += f"• Спорных: {disputed_analyses}\n\n"

        if last_analysis:
            stats_text += f"📅 *Последний анализ:*\n"
            stats_text += f"• ID: {last_analysis.id}\n"
            stats_text += f"• Статус: {last_analysis.status_emoji} {last_analysis.status}\n"
            if last_analysis.completed_at:
                stats_text += f"• Дата: {format_datetime(last_analysis.completed_at)}\n"
        else:
            stats_text += f"📅 Анализы еще не проводились"

        await message.answer(stats_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in show_my_statistics: {e}")
        await message.answer("❌ Ошибка при получении статистики")


@router.callback_query(F.data == "main_menu")
@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext, master: Master):
    """Возврат в главное меню"""
    try:
        await state.clear()

        try:
            await callback.message.edit_text(
                f"🏠 *Главное меню*\n\n"
                f"Добро пожаловать, {master.name}!\n"
                f"Выберите действие:",
                parse_mode="Markdown",
                reply_markup=get_master_main_menu()
            )
        except:
            # Если не можем отредактировать, отправляем новое сообщение
            await callback.message.answer(
                f"🏠 *Главное меню*\n\n"
                f"Добро пожаловать, {master.name}!\n"
                f"Выберите действие:",
                parse_mode="Markdown",
                reply_markup=get_master_main_menu()
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_main_menu: {e}")
        await callback.answer("❌ Ошибка")


# === ГЛАВНОЕ МЕНЮ МАСТЕРА ===
@router.message(F.text == "📸 Начать анализ")
async def start_analysis(message: Message, state: FSMContext, master: Master, db_session: AsyncSession):
    """Начало процесса анализа маникюра"""
    try:
        # Получаем свежую информацию о мастере и салоне
        master_query = select(Master).options(selectinload(Master.salon)).where(Master.id == master.id)
        result = await db_session.execute(master_query)
        master_with_salon = result.scalar_one_or_none()

        if not master_with_salon or not master_with_salon.salon:
            await message.answer(
                "❌ *Ошибка конфигурации*\n\n"
                "Информация о салоне не найдена.\n"
                "Обратитесь к администратору.",
                parse_mode="Markdown",
                reply_markup=get_master_main_menu()
            )
            return

        salon = master_with_salon.salon

        if salon.quota_remaining <= 0:
            await message.answer(
                f"❌ *Лимит анализов исчерпан*\n\n"
                f"🏢 Салон: {salon.name}\n"
                f"📊 Использовано: {salon.quota_used}/{salon.quota_limit}\n\n"
                f"💬 Обратитесь к владельцу для пополнения квот.",
                parse_mode="Markdown",
                reply_markup=get_master_main_menu()
            )
            return

        # Создаем новый анализ в статусе "начат"
        new_analysis = Analysis(
            master_id=master.id,
            salon_id=salon.id,
            status="started",
            first_hand_photos=[],
            second_hand_photos=[],
            survey_response=None,
            ai_first_analysis=None,
            ai_second_analysis=None,
            ai_diary=None,
            created_at=datetime.now()
        )

        db_session.add(new_analysis)
        await db_session.commit()
        await db_session.refresh(new_analysis)

        # Сохраняем ID анализа в состоянии
        await state.update_data(analysis_id=new_analysis.id)

        await message.answer(
            f"📸 *Начать анализ маникюра*\n\n"
            f"💰 Доступно анализов: {salon.quota_remaining}\n"
            f"🆔 ID анализа: {new_analysis.id}\n\n"
            f"📋 *Процесс анализа:*\n"
            f"1️⃣ Фото первой руки\n"
            f"2️⃣ Фото второй руки\n"
            f"3️⃣ Опрос мастера\n"
            f"4️⃣ ИИ анализ и дневник роста\n"
            f"5️⃣ Проверка результатов\n\n"
            f"💡 Квота спишется только после полного анализа\n\n"
            f"Начнем с первой руки:",
            parse_mode="Markdown",
            reply_markup=get_first_hand_keyboard()
        )
        await state.set_state(MasterStates.waiting_for_first_hand_photos)

    except Exception as e:
        logger.error(f"Error in start_analysis: {e}")
        await message.answer("❌ Ошибка при запуске анализа")


# === АНАЛИЗ ПЕРВОЙ РУКИ ===
@router.callback_query(F.data == "add_first_hand_photo", MasterStates.waiting_for_first_hand_photos)
async def request_first_hand_photo(callback: CallbackQuery):
    """Запрос фотографии первой руки"""
    try:
        # Удаляем старое сообщение и отправляем новое
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer(
            "📸 *Фото первой руки*\n\n"
            "Отправьте одну или несколько фотографий первой руки.\n"
            "После каждого фото можете добавить еще или перейти к следующему этапу.",
            parse_mode="Markdown",
            reply_markup=get_cancel_analysis_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in request_first_hand_photo: {e}")
        await callback.answer("❌ Ошибка")


@router.message(F.photo, MasterStates.waiting_for_first_hand_photos)
async def process_first_hand_photo(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка фотографии первой руки"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        if not analysis_id:
            await message.answer("❌ Ошибка: анализ не найден")
            return

        # Получаем фото наилучшего качества
        photo: PhotoSize = message.photo[-1]
        photo_file_id = photo.file_id

        # Получаем анализ из БД
        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if analysis:
            logger.info(f"Processing photo for analysis {analysis_id}")
            logger.info(f"Photos before: {analysis.first_hand_photos}")

            # ИСПРАВЛЕНИЕ: Правильное обновление JSON поля
            if analysis.first_hand_photos is None:
                analysis.first_hand_photos = []

            analysis.first_hand_photos.append(photo_file_id)

            # ВАЖНО: Уведомляем SQLAlchemy об изменении
            flag_modified(analysis, 'first_hand_photos')
            await db_session.commit()

            # Обновляем из БД для получения актуальных данных
            await db_session.refresh(analysis)
            photos_count = len(analysis.first_hand_photos)

            logger.info(f"Photos after commit: {analysis.first_hand_photos}")
            logger.info(f"Final count: {photos_count}")

            await message.answer_photo(
                photo=photo_file_id,
                caption=(
                    f"✅ *Фото первой руки добавлено*\n\n"
                    f"📸 Всего фото первой руки: {photos_count}\n\n"
                    f"Выберите действие:"
                ),
                parse_mode="Markdown",
                reply_markup=get_first_hand_actions_keyboard(photos_count)
            )

    except Exception as e:
        logger.error(f"Error in process_first_hand_photo: {e}")
        await message.answer("❌ Ошибка при обработке фото")


@router.callback_query(F.data == "view_first_hand_photos", MasterStates.waiting_for_first_hand_photos)
async def view_first_hand_photos(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Просмотр всех фото первой руки"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if not analysis or not analysis.first_hand_photos:
            await callback.answer("❌ Фото не найдены", show_alert=True)
            return

        # Отправляем все фото как медиа группу
        if len(analysis.first_hand_photos) == 1:
            await callback.message.answer_photo(
                photo=analysis.first_hand_photos[0],
                caption=f"📸 Фото первой руки (1 из 1)",
                reply_markup=get_first_hand_actions_keyboard(len(analysis.first_hand_photos))
            )
        else:
            # Если фото много, показываем первое с информацией
            await callback.message.answer_photo(
                photo=analysis.first_hand_photos[0],
                caption=(
                    f"📸 *Все фото первой руки*\n\n"
                    f"Показано фото 1 из {len(analysis.first_hand_photos)}\n"
                    f"Всего фотографий: {len(analysis.first_hand_photos)}"
                ),
                parse_mode="Markdown",
                reply_markup=get_first_hand_actions_keyboard(len(analysis.first_hand_photos))
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in view_first_hand_photos: {e}")
        await callback.answer("❌ Ошибка при просмотре фото", show_alert=True)


@router.callback_query(F.data == "remove_last_first_hand", MasterStates.waiting_for_first_hand_photos)
async def delete_last_first_photo(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Удаление последнего фото первой руки"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if not analysis or not analysis.first_hand_photos:
            await callback.answer("❌ Нет фото для удаления", show_alert=True)
            return

        # ИСПРАВЛЕНИЕ: Правильное удаление из JSON поля
        analysis.first_hand_photos.pop()
        flag_modified(analysis, 'first_hand_photos')
        await db_session.commit()
        await db_session.refresh(analysis)

        remaining_count = len(analysis.first_hand_photos)

        if remaining_count > 0:
            try:
                await callback.message.edit_caption(
                    caption=(
                        f"✅ *Последнее фото удалено*\n\n"
                        f"📸 Осталось фото первой руки: {remaining_count}\n\n"
                        f"Выберите действие:"
                    ),
                    parse_mode="Markdown",
                    reply_markup=get_first_hand_actions_keyboard(remaining_count)
                )
            except:
                # Если не можем отредактировать, отправляем новое сообщение
                await callback.message.answer(
                    f"✅ *Последнее фото удалено*\n\n"
                    f"📸 Осталось фото первой руки: {remaining_count}\n\n"
                    f"Выберите действие:",
                    parse_mode="Markdown",
                    reply_markup=get_first_hand_actions_keyboard(remaining_count)
                )
        else:
            try:
                await callback.message.edit_text(
                    "✅ *Все фото первой руки удалены*\n\n"
                    "Добавьте новые фотографии:",
                    parse_mode="Markdown",
                    reply_markup=get_first_hand_keyboard()
                )
            except:
                await callback.message.answer(
                    "✅ *Все фото первой руки удалены*\n\n"
                    "Добавьте новые фотографии:",
                    parse_mode="Markdown",
                    reply_markup=get_first_hand_keyboard()
                )

        await callback.answer("Фото удалено")

    except Exception as e:
        logger.error(f"Error in delete_last_first_photo: {e}")
        await callback.answer("❌ Ошибка при удалении фото", show_alert=True)


@router.callback_query(F.data == "continue_to_second_hand", MasterStates.waiting_for_first_hand_photos)
async def continue_to_second_hand(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Переход к фотографированию второй руки"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        # Проверяем, что есть хотя бы одно фото первой руки
        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if not analysis or not analysis.first_hand_photos:
            await callback.answer("❌ Добавьте хотя бы одно фото первой руки", show_alert=True)
            return

        # Удаляем старое сообщение и отправляем новое
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer(
            f"✅ *Первая рука готова*\n\n"
            f"📸 Добавлено фото: {len(analysis.first_hand_photos)}\n\n"
            f"Теперь сфотографируйте вторую руку:",
            parse_mode="Markdown",
            reply_markup=get_second_hand_keyboard()
        )
        await state.set_state(MasterStates.waiting_for_second_hand_photos)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in continue_to_second_hand: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# === ВОЗВРАТ К ПЕРВОЙ РУКЕ ===
@router.callback_query(F.data == "back_to_first_hand", MasterStates.waiting_for_second_hand_photos)
async def back_to_first_hand(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Возврат к первой руке"""
    try:
        await state.set_state(MasterStates.waiting_for_first_hand_photos)

        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        photos_count = len(analysis.first_hand_photos or []) if analysis else 0

        await callback.message.edit_text(
            f"📸 *Редактирование первой руки*\n\n"
            f"📊 Текущее количество фото: {photos_count}\n\n"
            f"Выберите действие:",
            parse_mode="Markdown",
            reply_markup=get_first_hand_actions_keyboard(
                photos_count) if photos_count > 0 else get_first_hand_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_first_hand: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# === АНАЛИЗ ВТОРОЙ РУКИ ===
@router.callback_query(F.data == "add_second_hand_photo", MasterStates.waiting_for_second_hand_photos)
async def request_second_hand_photo(callback: CallbackQuery):
    """Запрос фотографии второй руки"""
    try:
        # Удаляем старое сообщение и отправляем новое
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer(
            "📸 *Фото второй руки*\n\n"
            "Отправьте одну или несколько фотографий второй руки.\n"
            "После каждого фото можете добавить еще или перейти к опросу.",
            parse_mode="Markdown",
            reply_markup=get_cancel_analysis_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in request_second_hand_photo: {e}")
        await callback.answer("❌ Ошибка")


@router.message(F.photo, MasterStates.waiting_for_second_hand_photos)
async def process_second_hand_photo(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка фотографии второй руки"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        if not analysis_id:
            await message.answer("❌ Ошибка: анализ не найден")
            return

        # Получаем фото наилучшего качества
        photo: PhotoSize = message.photo[-1]
        photo_file_id = photo.file_id

        # Обновляем анализ в БД
        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if analysis:
            # ИСПРАВЛЕНИЕ: Правильное обновление JSON поля
            if analysis.second_hand_photos is None:
                analysis.second_hand_photos = []

            analysis.second_hand_photos.append(photo_file_id)
            flag_modified(analysis, 'second_hand_photos')
            await db_session.commit()
            await db_session.refresh(analysis)

            photos_count = len(analysis.second_hand_photos)
            await message.answer_photo(
                photo=photo_file_id,
                caption=(
                    f"✅ *Фото второй руки добавлено*\n\n"
                    f"📸 Всего фото второй руки: {photos_count}\n\n"
                    f"Выберите действие:"
                ),
                parse_mode="Markdown",
                reply_markup=get_second_hand_actions_keyboard(photos_count)
            )

    except Exception as e:
        logger.error(f"Error in process_second_hand_photo: {e}")
        await message.answer("❌ Ошибка при обработке фото")


@router.callback_query(F.data == "view_second_hand_photos", MasterStates.waiting_for_second_hand_photos)
async def view_second_hand_photos(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Просмотр всех фото второй руки"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if not analysis or not analysis.second_hand_photos:
            await callback.answer("❌ Фото не найдены", show_alert=True)
            return

        # Отправляем первое фото с информацией
        await callback.message.answer_photo(
            photo=analysis.second_hand_photos[0],
            caption=(
                f"📸 *Все фото второй руки*\n\n"
                f"Показано фото 1 из {len(analysis.second_hand_photos)}\n"
                f"Всего фотографий: {len(analysis.second_hand_photos)}"
            ),
            parse_mode="Markdown",
            reply_markup=get_second_hand_actions_keyboard(len(analysis.second_hand_photos))
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in view_second_hand_photos: {e}")
        await callback.answer("❌ Ошибка при просмотре фото", show_alert=True)


@router.callback_query(F.data == "remove_last_second_hand", MasterStates.waiting_for_second_hand_photos)
async def delete_last_second_photo(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Удаление последнего фото второй руки"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if not analysis or not analysis.second_hand_photos:
            await callback.answer("❌ Нет фото для удаления", show_alert=True)
            return

        # ИСПРАВЛЕНИЕ: Правильное удаление из JSON поля
        analysis.second_hand_photos.pop()
        flag_modified(analysis, 'second_hand_photos')
        await db_session.commit()
        await db_session.refresh(analysis)

        remaining_count = len(analysis.second_hand_photos)

        if remaining_count > 0:
            try:
                await callback.message.edit_caption(
                    caption=(
                        f"✅ *Последнее фото удалено*\n\n"
                        f"📸 Осталось фото второй руки: {remaining_count}\n\n"
                        f"Выберите действие:"
                    ),
                    parse_mode="Markdown",
                    reply_markup=get_second_hand_actions_keyboard(remaining_count)
                )
            except:
                await callback.message.answer(
                    f"✅ *Последнее фото удалено*\n\n"
                    f"📸 Осталось фото второй руки: {remaining_count}\n\n"
                    f"Выберите действие:",
                    parse_mode="Markdown",
                    reply_markup=get_second_hand_actions_keyboard(remaining_count)
                )
        else:
            try:
                await callback.message.edit_text(
                    "✅ *Все фото второй руки удалены*\n\n"
                    "Добавьте новые фотографии:",
                    parse_mode="Markdown",
                    reply_markup=get_second_hand_keyboard()
                )
            except:
                await callback.message.answer(
                    "✅ *Все фото второй руки удалены*\n\n"
                    "Добавьте новые фотографии:",
                    parse_mode="Markdown",
                    reply_markup=get_second_hand_keyboard()
                )

        await callback.answer("Фото удалено")

    except Exception as e:
        logger.error(f"Error in delete_last_second_photo: {e}")
        await callback.answer("❌ Ошибка при удалении фото", show_alert=True)


@router.callback_query(F.data == "continue_to_survey", MasterStates.waiting_for_second_hand_photos)
async def continue_to_survey(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Переход к опросу мастера"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        # Проверяем, что есть хотя бы одно фото второй руки
        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if not analysis or not analysis.second_hand_photos:
            await callback.answer("❌ Добавьте хотя бы одно фото второй руки", show_alert=True)
            return

        # Удаляем старое сообщение и отправляем новое
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer(
            f"✅ *Фотографирование завершено*\n\n"
            f"📸 Фото первой руки: {len(analysis.first_hand_photos)}\n"
            f"📸 Фото второй руки: {len(analysis.second_hand_photos)}\n\n"
            f"📋 *Вопрос мастеру:*\n\n"
            f"Опишите состояние ногтей клиента и особенности, которые заметили:\n"
            f"(состояние кутикулы, форма ногтей, проблемы, пожелания клиента)",
            parse_mode="Markdown",
            reply_markup=get_cancel_analysis_keyboard()
        )
        await state.set_state(MasterStates.waiting_for_survey_response)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in continue_to_survey: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# === ОПРОС МАСТЕРА ===
@router.message(F.text, MasterStates.waiting_for_survey_response)
async def process_survey_response(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка ответа мастера на опрос"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        if not analysis_id:
            await message.answer("❌ Ошибка: анализ не найден")
            return

        survey_response = message.text.strip()

        if len(survey_response) < 10:
            await message.answer(
                "❌ Слишком короткий ответ\n\n"
                "Пожалуйста, опишите более подробно состояние ногтей клиента:"
            )
            return

        # Обновляем анализ в БД
        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if analysis:
            analysis.survey_response = survey_response
            analysis.status = "ready_for_ai"
            await db_session.commit()

            await message.answer(
                f"✅ *Данные собраны*\n\n"
                f"📸 Фото первой руки: {len(analysis.first_hand_photos)}\n"
                f"📸 Фото второй руки: {len(analysis.second_hand_photos)}\n"
                f"📝 Ответ мастера: получен\n\n"
                f"🤖 Запустить ИИ анализ?",
                parse_mode="Markdown",
                reply_markup=get_start_ai_analysis_keyboard()
            )
            await state.set_state(MasterStates.ready_for_ai_analysis)

    except Exception as e:
        logger.error(f"Error in process_survey_response: {e}")
        await message.answer("❌ Ошибка при обработке ответа")


# === РЕДАКТИРОВАНИЕ ОТВЕТА ===
@router.callback_query(F.data == "edit_survey_response", MasterStates.ready_for_ai_analysis)
async def edit_survey_response(callback: CallbackQuery, state: FSMContext):
    """Редактирование ответа на опрос"""
    try:
        await callback.message.edit_text(
            f"✏️ *Редактирование ответа*\n\n"
            f"📋 Введите новый ответ на вопрос:\n\n"
            f"Опишите состояние ногтей клиента и особенности, которые заметили:",
            parse_mode="Markdown",
            reply_markup=get_cancel_analysis_keyboard()
        )
        await state.set_state(MasterStates.waiting_for_survey_response)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in edit_survey_response: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# === ИИ АНАЛИЗ ===
@router.callback_query(F.data == "start_ai_analysis", MasterStates.ready_for_ai_analysis)
async def start_ai_analysis(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Запуск ИИ анализа"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        # Получаем анализ
        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if not analysis:
            await callback.answer("❌ Анализ не найден", show_alert=True)
            return

        analysis.status = "ai_analyzing"
        analysis.ai_started_at = datetime.now()
        await db_session.commit()

        await callback.message.edit_text(
            f"🤖 *ИИ анализ запущен*\n\n"
            f"⏳ Анализ первой руки...\n"
            f"⏳ Анализ второй руки...\n"
            f"⏳ Создание дневника роста...\n\n"
            f"Пожалуйста, подождите 2-3 минуты.",
            parse_mode="Markdown"
        )

        # === ЗДЕСЬ ИНТЕГРАЦИЯ С ВАШИМ ИИ ===
        try:
            # 1. Анализ первой руки
            first_hand_result = await analyze_first_hand_ai(
                photos=analysis.first_hand_photos,
                survey_data=analysis.survey_response
            )
            analysis.ai_first_analysis = first_hand_result

            # 2. Анализ второй руки
            second_hand_result = await analyze_second_hand_ai(
                photos=analysis.second_hand_photos,
                survey_data=analysis.survey_response
            )
            analysis.ai_second_analysis = second_hand_result

            # 3. Создание дневника роста
            diary_result = await generate_growth_diary_ai(
                first_analysis=first_hand_result,
                second_analysis=second_hand_result,
                survey_data=analysis.survey_response
            )
            analysis.ai_diary = diary_result

            analysis.status = "ai_completed"
            analysis.completed_at = datetime.now()
            analysis.ai_completed_at = datetime.now()
            await db_session.commit()

            await callback.message.edit_text(
                f"✅ *ИИ анализ завершен*\n\n"
                f"📊 Результаты готовы к просмотру",
                parse_mode="Markdown",
                reply_markup=get_view_results_keyboard()
            )
            await state.set_state(MasterStates.reviewing_results)

        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            analysis.status = "ai_error"
            await db_session.commit()

            await callback.message.edit_text(
                f"❌ *Ошибка ИИ анализа*\n\n"
                f"Попробуйте еще раз или обратитесь к администратору.",
                parse_mode="Markdown",
                reply_markup=get_retry_analysis_keyboard()
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in start_ai_analysis: {e}")
        await callback.answer("❌ Ошибка запуска анализа", show_alert=True)


@router.callback_query(F.data == "retry_ai_analysis")
async def retry_ai_analysis(callback: CallbackQuery, state: FSMContext):
    """Повторная попытка ИИ анализа"""
    try:
        # Возвращаемся к предыдущему состоянию
        await state.set_state(MasterStates.ready_for_ai_analysis)

        await callback.message.edit_text(
            f"🔄 *Повторная попытка анализа*\n\n"
            f"Данные сохранены. Запустить анализ заново?",
            parse_mode="Markdown",
            reply_markup=get_start_ai_analysis_keyboard()
        )
        await callback.answer("Готов к повторной попытке")

    except Exception as e:
        logger.error(f"Error in retry_ai_analysis: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# === ПРОСМОТР РЕЗУЛЬТАТОВ ===
@router.callback_query(F.data == "view_results", MasterStates.reviewing_results)
async def view_analysis_results(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Просмотр результатов анализа"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if not analysis or analysis.status != "ai_completed":
            await callback.answer("❌ Результаты не готовы", show_alert=True)
            return

        # Формируем сообщение с результатами
        results_text = format_analysis_results(analysis)

        await callback.message.edit_text(
            results_text,
            parse_mode="Markdown",
            reply_markup=get_results_action_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in view_analysis_results: {e}")
        await callback.answer("❌ Ошибка при просмотре результатов", show_alert=True)


@router.callback_query(F.data == "accept_results", MasterStates.reviewing_results)
async def accept_results(callback: CallbackQuery, state: FSMContext, master: Master, db_session: AsyncSession):
    """Принятие результатов анализа"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        # Получаем анализ и обновляем статус
        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if analysis:
            analysis.status = "completed"

            # СПИСЫВАЕМ КВОТУ ТОЛЬКО СЕЙЧАС!
            salon_query = select(Salon).where(Salon.id == analysis.salon_id)
            salon_result = await db_session.execute(salon_query)
            salon = salon_result.scalar_one_or_none()

            if salon:
                salon.quota_used += 1

            # Увеличиваем счетчик анализов мастера
            master.analyses_count += 1

            await db_session.commit()

            await callback.message.edit_text(
                f"✅ *Анализ завершен успешно!*\n\n"
                f"🆔 ID анализа: {analysis.id}\n"
                f"📊 Квота списана: 1\n"
                f"💰 Осталось анализов: {salon.quota_remaining}\n\n"
                f"Спасибо за работу!",
                parse_mode="Markdown",
                reply_markup=get_main_menu_button()
            )

            await state.clear()
            logger.info(f"Analysis {analysis.id} completed successfully by master {master.name}")

        await callback.answer("Анализ завершен!")

    except Exception as e:
        logger.error(f"Error in accept_results: {e}")
        await callback.answer("❌ Ошибка при завершении анализа", show_alert=True)


@router.callback_query(F.data == "dispute_results", MasterStates.reviewing_results)
async def dispute_results(callback: CallbackQuery, state: FSMContext):
    """Оспаривание результатов анализа"""
    try:
        await callback.message.edit_text(
            f"⚠️ *Оспаривание результатов*\n\n"
            f"Опишите, что именно вас не устраивает в результатах анализа:",
            parse_mode="Markdown",
            reply_markup=get_cancel_dispute_keyboard()
        )
        await state.set_state(MasterStates.disputing_results)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in dispute_results: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_dispute", MasterStates.disputing_results)
async def cancel_dispute(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Отмена оспаривания результатов"""
    try:
        # Возвращаемся к просмотру результатов
        await state.set_state(MasterStates.reviewing_results)

        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if analysis:
            results_text = format_analysis_results(analysis)
            await callback.message.edit_text(
                results_text,
                parse_mode="Markdown",
                reply_markup=get_results_action_keyboard()
            )

        await callback.answer("Оспаривание отменено")

    except Exception as e:
        logger.error(f"Error in cancel_dispute: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(F.text, MasterStates.disputing_results)
async def process_dispute(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обработка жалобы на результаты"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')
        dispute_reason = message.text.strip()

        # Обновляем анализ
        analysis_query = select(Analysis).where(Analysis.id == analysis_id)
        result = await db_session.execute(analysis_query)
        analysis = result.scalar_one_or_none()

        if analysis:
            analysis.status = "disputed"
            if not analysis.result_data:
                analysis.result_data = {}
            analysis.result_data['dispute_reason'] = dispute_reason
            analysis.result_data['dispute_date'] = datetime.now().isoformat()
            flag_modified(analysis, 'result_data')
            await db_session.commit()

            await message.answer(
                f"📝 *Жалоба зарегистрирована*\n\n"
                f"🆔 ID анализа: {analysis.id}\n"
                f"📞 Администратор рассмотрит вашу жалобу\n\n"
                f"⚠️ Квота не будет списана до решения спора",
                parse_mode="Markdown",
                reply_markup=get_main_menu_button()
            )

            await state.clear()
            logger.info(f"Analysis {analysis.id} disputed by master")

    except Exception as e:
        logger.error(f"Error in process_dispute: {e}")
        await message.answer("❌ Ошибка при регистрации жалобы")


# === ПОДЕЛИТЬСЯ И СОХРАНИТЬ РЕЗУЛЬТАТЫ ===
@router.callback_query(F.data == "share_results")
async def share_results(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Поделиться результатами"""
    try:
        # Заглушка для функции поделиться
        await callback.answer("🚧 Функция в разработке", show_alert=True)

    except Exception as e:
        logger.error(f"Error in share_results: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "save_results")
async def save_results(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Сохранить результаты"""
    try:
        # Заглушка для функции сохранения
        await callback.answer("🚧 Функция в разработке", show_alert=True)

    except Exception as e:
        logger.error(f"Error in save_results: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# === КОНТАКТ С ПОДДЕРЖКОЙ ===
@router.callback_query(F.data == "contact_support")
async def contact_support(callback: CallbackQuery):
    """Контакт с поддержкой"""
    try:
        await callback.message.edit_text(
            f"📞 *Техническая поддержка*\n\n"
            f"По техническим вопросам обращайтесь:\n"
            f"• Telegram: @support_username\n"
            f"• Email: support@example.com\n"
            f"• Телефон: +7 (XXX) XXX-XX-XX\n\n"
            f"🕐 Время работы: 9:00 - 18:00",
            parse_mode="Markdown",
            reply_markup=get_main_menu_button()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in contact_support: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# === ОТМЕНА АНАЛИЗА ===
@router.callback_query(F.data == "cancel_analysis")
async def cancel_analysis(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Отмена анализа"""
    try:
        data = await state.get_data()
        analysis_id = data.get('analysis_id')

        if analysis_id:
            # Удаляем незавершенный анализ
            analysis_query = select(Analysis).where(Analysis.id == analysis_id)
            result = await db_session.execute(analysis_query)
            analysis = result.scalar_one_or_none()

            if analysis and analysis.status in ['started', 'ready_for_ai', 'ai_analyzing']:
                await db_session.delete(analysis)
                await db_session.commit()

        await state.clear()

        try:
            await callback.message.edit_text(
                "❌ *Анализ отменен*\n\n"
                "Квота не была списана.",
                parse_mode="Markdown",
                reply_markup=get_main_menu_button()
            )
        except:
            # Если не можем отредактировать, отправляем новое сообщение
            await callback.message.answer(
                "❌ *Анализ отменен*\n\n"
                "Квота не была списана.",
                parse_mode="Markdown",
                reply_markup=get_main_menu_button()
            )

        await callback.answer("Анализ отменен")

    except Exception as e:
        logger.error(f"Error in cancel_analysis: {e}")
        await callback.answer("❌ Ошибка при отмене анализа", show_alert=True)


# === ПРОВЕРКА ОСТАТКА КВОТ ===
@router.message(F.text == "💰 Остаток анализов")
async def check_quota(message: Message, master: Master, db_session: AsyncSession):
    """Проверка остатка анализов"""
    try:
        master_query = select(Master).options(selectinload(Master.salon)).where(Master.id == master.id)
        result = await db_session.execute(master_query)
        master_with_salon = result.scalar_one_or_none()

        if not master_with_salon or not master_with_salon.salon:
            await message.answer(
                "❌ Информация о салоне не найдена.",
                reply_markup=get_master_main_menu()
            )
            return

        salon = master_with_salon.salon
        quota_percentage = (salon.quota_used / salon.quota_limit * 100) if salon.quota_limit > 0 else 0

        status_emoji = "🟢" if salon.quota_remaining > 10 else "🟡" if salon.quota_remaining > 0 else "🔴"

        await message.answer(
            f"{status_emoji} *Информация о квотах*\n\n"
            f"🏢 Салон: {salon.name}\n"
            f"🏙️ Город: {salon.city}\n\n"
            f"💰 Доступно анализов: {salon.quota_remaining}\n"
            f"📊 Использовано: {salon.quota_used}/{salon.quota_limit}\n"
            f"📈 Процент использования: {quota_percentage:.1f}%\n\n"
            f"👤 Ваши анализы: {master_with_salon.analyses_count}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in check_quota: {e}")
        await message.answer("❌ Ошибка при получении информации о квотах")


# === ФУНКЦИИ ИИ ИНТЕГРАЦИИ (ЗАГОТОВКИ) ===
async def analyze_first_hand_ai(photos: List[str], survey_data: str) -> dict:
    """
    ЗАГОТОВКА для анализа первой руки

    ЗДЕСЬ ВСТАВЬТЕ ВАШ ПРОМПТ ДЛЯ ПЕРВОЙ РУКИ и API подключение

    Args:
        photos: Список file_id фотографий первой руки
        survey_data: Ответ мастера на опрос

    Returns:
        dict: Результат анализа первой руки
    """
    # ВАШ_ПРОМПТ_ПЕРВАЯ_РУКА = """
    # Проанализируй состояние ногтей на первой руке...
    # """

    # ВАШ_API_КОД_ЗДЕСЬ
    # result = await your_ai_api.analyze(photos, ВАШ_ПРОМПТ_ПЕРВАЯ_РУКА, survey_data)

    # Временная заглушка
    return {
        "status": "analyzed",
        "hand": "first",
        "photos_count": len(photos),
        "analysis": "Анализ первой руки выполнен (заглушка)",
        "timestamp": datetime.now().isoformat()
    }


async def analyze_second_hand_ai(photos: List[str], survey_data: str) -> dict:
    """
    ЗАГОТОВКА для анализа второй руки

    ЗДЕСЬ ВСТАВЬТЕ ВАШ ПРОМПТ ДЛЯ ВТОРОЙ РУКИ и API подключение
    """
    # ВАШ_ПРОМПТ_ВТОРАЯ_РУКА = """
    # Проанализируй состояние ногтей на второй руке...
    # """

    # ВАШ_API_КОД_ЗДЕСЬ

    # Временная заглушка
    return {
        "status": "analyzed",
        "hand": "second",
        "photos_count": len(photos),
        "analysis": "Анализ второй руки выполнен (заглушка)",
        "timestamp": datetime.now().isoformat()
    }


async def generate_growth_diary_ai(first_analysis: dict, second_analysis: dict, survey_data: str) -> dict:
    """
    ЗАГОТОВКА для создания дневника роста

    ЗДЕСЬ ВСТАВЬТЕ ВАШ ПРОМПТ ДЛЯ ДНЕВНИКА РОСТА и API подключение
    """
    # ВАШ_ПРОМПТ_ДНЕВНИК_РОСТА = """
    # На основе анализа двух рук создай дневник роста ногтей...
    # """

    # ВАШ_API_КОД_ЗДЕСЬ

    # Временная заглушка
    return {
        "status": "generated",
        "diary": "Дневник роста создан (заглушка)",
        "recommendations": "Рекомендации по уходу",
        "timestamp": datetime.now().isoformat()
    }


def format_analysis_results(analysis: Analysis) -> str:
    """Форматирование результатов анализа для показа мастеру"""
    try:
        completed_at_str = "Не указано"
        if analysis.completed_at:
            completed_at_str = format_datetime(analysis.completed_at)

        first_analysis = "Нет данных"
        second_analysis = "Нет данных"
        diary = "Нет данных"
        recommendations = "Нет данных"

        if analysis.ai_first_analysis:
            first_analysis = analysis.ai_first_analysis.get('analysis', 'Нет данных')

        if analysis.ai_second_analysis:
            second_analysis = analysis.ai_second_analysis.get('analysis', 'Нет данных')

        if analysis.ai_diary:
            diary = analysis.ai_diary.get('diary', 'Нет данных')
            recommendations = analysis.ai_diary.get('recommendations', 'Нет данных')

        return f"""📊 *Результаты анализа*

🆔 ID: {analysis.id}
📅 Завершен: {completed_at_str}

📸 *Фото:*
• Первая рука: {len(analysis.first_hand_photos or [])} фото
• Вторая рука: {len(analysis.second_hand_photos or [])} фото

🤖 *ИИ Анализ:*
• Первая рука: {first_analysis}
• Вторая рука: {second_analysis}

📖 *Дневник роста:*
{diary}

💡 *Рекомендации:*
{recommendations}

Принимаете результаты?"""

    except Exception as e:
        logger.error(f"Error in format_analysis_results: {e}")
        return f"📊 *Результаты анализа*\n\n🆔 ID: {analysis.id}\n\n❌ Ошибка форматирования результатов"


# === ОБРАБОТЧИК ПО УМОЛЧАНИЮ ===
@router.message()
async def handle_unknown_message(message: Message, master: Master):
    """Обработка неизвестных сообщений от мастеров"""
    try:
        # Проверяем, есть ли у сообщения текст
        if not message.text:
            await message.answer(
                f"👋 Привет, {master.name}!\n\n"
                f"Отправьте текстовое сообщение или используйте кнопки меню:",
                reply_markup=get_master_main_menu()
            )
            return

        # Логируем неизвестную команду для отладки
        logger.warning(f"Unknown command from master {master.id}: '{message.text}'")

        await message.answer(
            f"👋 Привет, {master.name}!\n\n"
            f"Я не понимаю команду: «{message.text}»\n\n"
            f"Используйте кнопки меню для навигации:",
            reply_markup=get_master_main_menu()
        )

    except Exception as e:
        logger.error(f"Error in handle_unknown_message: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_master_main_menu()
        )