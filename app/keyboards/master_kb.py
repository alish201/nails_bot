from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_master_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню мастера"""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="📸 Начать анализ"),
        KeyboardButton(text="💰 Остаток анализов"),
        KeyboardButton(text="📖 Инструкция"),
        KeyboardButton(text="📊 Моя статистика")
    )
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


# === КЛАВИАТУРЫ ДЛЯ МНОГОЭТАПНОГО АНАЛИЗА ===

def get_first_hand_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для начала фотографирования первой руки"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📸 Добавить фото первой руки", callback_data="add_first_hand_photo"),
        InlineKeyboardButton(text="❌ Отменить анализ", callback_data="cancel_analysis")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_first_hand_actions_keyboard(photos_count: int) -> InlineKeyboardMarkup:
    """Клавиатура действий после добавления фото первой руки"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=f"📸 Добавить еще фото ({photos_count})", callback_data="add_first_hand_photo"),
        InlineKeyboardButton(text="👁️ Просмотр фото", callback_data="view_first_hand_photos"),
        InlineKeyboardButton(text="➡️ К второй руке", callback_data="continue_to_second_hand"),
        InlineKeyboardButton(text="🗑️ Удалить последнее", callback_data="remove_last_first_hand"),
        InlineKeyboardButton(text="❌ Отменить анализ", callback_data="cancel_analysis")
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_second_hand_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для начала фотографирования второй руки"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📸 Добавить фото второй руки", callback_data="add_second_hand_photo"),
        InlineKeyboardButton(text="⬅️ К первой руке", callback_data="back_to_first_hand"),
        InlineKeyboardButton(text="❌ Отменить анализ", callback_data="cancel_analysis")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_second_hand_actions_keyboard(photos_count: int) -> InlineKeyboardMarkup:
    """Клавиатура действий после добавления фото второй руки"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=f"📸 Добавить еще фото ({photos_count})", callback_data="add_second_hand_photo"),
        InlineKeyboardButton(text="👁️ Просмотр фото", callback_data="view_second_hand_photos"),
        InlineKeyboardButton(text="➡️ К опросу", callback_data="continue_to_survey"),
        InlineKeyboardButton(text="🗑️ Удалить последнее", callback_data="remove_last_second_hand"),
        InlineKeyboardButton(text="❌ Отменить анализ", callback_data="cancel_analysis")
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_start_ai_analysis_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура запуска ИИ анализа"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🤖 Запустить ИИ анализ", callback_data="start_ai_analysis"),
        InlineKeyboardButton(text="✏️ Изменить ответ", callback_data="edit_survey_response"),
        InlineKeyboardButton(text="❌ Отменить анализ", callback_data="cancel_analysis")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_view_results_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура просмотра результатов"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="👁️ Посмотреть результаты", callback_data="view_results")
    )
    return builder.as_markup()


def get_results_action_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура действий с результатами"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Принять результаты", callback_data="accept_results"),
        InlineKeyboardButton(text="⚠️ Оспорить результаты", callback_data="dispute_results"),
        InlineKeyboardButton(text="📤 Поделиться результатами", callback_data="share_results"),
        InlineKeyboardButton(text="💾 Сохранить результаты", callback_data="save_results")
    )
    builder.adjust(2, 2)
    return builder.as_markup()


def get_retry_analysis_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура повторного анализа при ошибке"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔄 Повторить анализ", callback_data="retry_ai_analysis"),
        InlineKeyboardButton(text="📞 Связаться с поддержкой", callback_data="contact_support"),
        InlineKeyboardButton(text="❌ Отменить анализ", callback_data="cancel_analysis")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_dispute_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены оспаривания"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="❌ Отменить оспаривание", callback_data="cancel_dispute")
    )
    return builder.as_markup()


def get_cancel_analysis_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура отмены анализа"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="❌ Отменить анализ", callback_data="cancel_analysis")
    )
    return builder.as_markup()


def get_main_menu_button() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    return builder.as_markup()


# === СУЩЕСТВУЮЩИЕ КЛАВИАТУРЫ (БЕЗ ИЗМЕНЕНИЙ) ===

def get_analysis_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для анализа"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📸 Отправить фото", callback_data="send_photo"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_analysis")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_photo_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения фото"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Начать анализ", callback_data="confirm_analysis"),
        InlineKeyboardButton(text="🔄 Отправить другое фото", callback_data="resend_photo"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_analysis")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_instructions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура инструкций"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📋 Как делать фото", callback_data="photo_instructions"),
        InlineKeyboardButton(text="🔍 Что анализируется", callback_data="analysis_info"),
        InlineKeyboardButton(text="🤖 Процесс ИИ анализа", callback_data="ai_process_info"),
        InlineKeyboardButton(text="⚖️ Система оспаривания", callback_data="dispute_info"),
        InlineKeyboardButton(text="❓ Частые вопросы", callback_data="faq"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def get_statistics_master_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура статистики мастера"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📈 За сегодня", callback_data="stats_today"),
        InlineKeyboardButton(text="📅 За неделю", callback_data="stats_week"),
        InlineKeyboardButton(text="📆 За месяц", callback_data="stats_month"),
        InlineKeyboardButton(text="📊 Все анализы", callback_data="stats_all"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_back_to_instructions() -> InlineKeyboardMarkup:
    """Кнопка возврата к инструкциям"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 К инструкциям", callback_data="back_to_instructions"))
    return builder.as_markup()


def get_analysis_history_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура истории анализов"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📋 Последние 10 анализов", callback_data="recent_analyses"),
        InlineKeyboardButton(text="🔍 Поиск по ID", callback_data="search_analysis"),
        InlineKeyboardButton(text="📊 Статистика по статусам", callback_data="status_stats"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def get_analysis_details_keyboard(analysis_id: int) -> InlineKeyboardMarkup:
    """Клавиатура деталей конкретного анализа"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="👁️ Посмотреть фото", callback_data=f"view_photos_{analysis_id}"),
        InlineKeyboardButton(text="📄 Полный отчет", callback_data=f"full_report_{analysis_id}"),
        InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_analysis_{analysis_id}"),
        InlineKeyboardButton(text="🔙 К истории", callback_data="analysis_history")
    )
    builder.adjust(2, 1, 1)
    return builder.as_markup()


# === ДОПОЛНИТЕЛЬНЫЕ КЛАВИАТУРЫ ДЛЯ РАСШИРЕННОГО ФУНКЦИОНАЛА ===

def get_photo_management_keyboard(hand: str) -> InlineKeyboardMarkup:
    """Клавиатура управления фотографиями"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📸 Добавить фото", callback_data=f"add_{hand}_photo"),
        InlineKeyboardButton(text="👁️ Просмотреть все фото", callback_data=f"view_{hand}_photos"),
        InlineKeyboardButton(text="🗑️ Удалить последнее", callback_data=f"remove_last_{hand}"),
        InlineKeyboardButton(text="🔄 Заменить последнее", callback_data=f"replace_last_{hand}"),
        InlineKeyboardButton(text="➡️ Продолжить", callback_data=f"continue_from_{hand}")
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_survey_help_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура помощи при заполнении опроса"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💡 Что писать в ответе?", callback_data="survey_help"),
        InlineKeyboardButton(text="📝 Примеры ответов", callback_data="survey_examples"),
        InlineKeyboardButton(text="❌ Отменить анализ", callback_data="cancel_analysis")
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def get_ai_progress_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время работы ИИ"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔄 Обновить статус", callback_data="refresh_ai_status"),
        InlineKeyboardButton(text="⏹️ Остановить анализ", callback_data="stop_ai_analysis")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_export_options_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура опций экспорта результатов"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📱 Отправить в чат", callback_data="export_to_chat"),
        InlineKeyboardButton(text="📧 Отправить на email", callback_data="export_to_email"),
        InlineKeyboardButton(text="💾 Сохранить как PDF", callback_data="export_to_pdf"),
        InlineKeyboardButton(text="📋 Скопировать текст", callback_data="copy_results"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_results")
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_dispute_options_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура опций оспаривания"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="❌ Неточный анализ", callback_data="dispute_inaccurate"),
        InlineKeyboardButton(text="📸 Проблемы с фото", callback_data="dispute_photo_quality"),
        InlineKeyboardButton(text="🤖 Ошибка ИИ", callback_data="dispute_ai_error"),
        InlineKeyboardButton(text="📝 Другая причина", callback_data="dispute_other"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_dispute")
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()