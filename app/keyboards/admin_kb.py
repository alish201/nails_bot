from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Optional


def get_admin_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню администратора"""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="🏢 Управление салонами"),
        KeyboardButton(text="👤 Управление мастерами"),
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="💰 Пополнить квоты"),
        KeyboardButton(text="⚙️ Настройки")
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_salons_menu() -> InlineKeyboardMarkup:
    """Меню управления салонами"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Добавить салон", callback_data="add_salon"),
        InlineKeyboardButton(text="📋 Список салонов", callback_data="list_salons"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_masters_menu() -> InlineKeyboardMarkup:
    """Меню управления мастерами"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Добавить мастера", callback_data="add_master"),
        InlineKeyboardButton(text="📋 Список мастеров", callback_data="list_masters"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_salon_list_keyboard(salons: List[dict]) -> InlineKeyboardMarkup:
    """Клавиатура со списком салонов"""
    builder = InlineKeyboardBuilder()

    for salon in salons:
        builder.add(
            InlineKeyboardButton(
                text=f"🏢 {salon['name']} ({salon['city']})",
                callback_data=f"salon_{salon['id']}"
            )
        )

    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_salons"))
    builder.adjust(1)
    return builder.as_markup()


def get_salon_actions_keyboard(salon_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с салоном"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_salon_{salon_id}"),
        InlineKeyboardButton(text="💰 Пополнить квоты", callback_data=f"add_quota_{salon_id}"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_salon_{salon_id}"),
        InlineKeyboardButton(text="🔙 К списку", callback_data="list_salons")
    )
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def get_salon_edit_keyboard(salon_id: int) -> InlineKeyboardMarkup:
    """Клавиатура редактирования салона"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📝 Изменить название", callback_data=f"edit_salon_name_{salon_id}"),
        InlineKeyboardButton(text="🏙️ Изменить город", callback_data=f"edit_salon_city_{salon_id}"),
        InlineKeyboardButton(text="💰 Изменить квоты", callback_data=f"edit_salon_quota_{salon_id}"),
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"salon_{salon_id}")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_master_list_keyboard(masters: List[dict]) -> InlineKeyboardMarkup:
    """Клавиатура со списком мастеров"""
    builder = InlineKeyboardBuilder()

    for master in masters:
        builder.add(
            InlineKeyboardButton(
                text=f"👤 {master['name']} ({master['salon_name']})",
                callback_data=f"master_{master['id']}"
            )
        )

    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_masters"))
    builder.adjust(1)
    return builder.as_markup()


def get_master_actions_keyboard(master_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с мастером"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_master_{master_id}"),
        InlineKeyboardButton(text="🔄 Сменить салон", callback_data=f"change_salon_{master_id}"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_master_{master_id}"),
        InlineKeyboardButton(text="🔙 К списку", callback_data="list_masters")
    )
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def get_master_edit_keyboard(master_id: int) -> InlineKeyboardMarkup:
    """Клавиатура редактирования мастера"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📝 Изменить имя", callback_data=f"edit_master_name_{master_id}"),
        InlineKeyboardButton(text="💬 Изменить Telegram ID", callback_data=f"edit_master_telegram_{master_id}"),
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"master_{master_id}")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_salon_selection_keyboard(salons: List[dict], action: str,
                                 master_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора салона"""
    builder = InlineKeyboardBuilder()

    for salon in salons:
        callback_data = f"{action}_{salon['id']}"
        if master_id:
            callback_data += f"_{master_id}"

        builder.add(
            InlineKeyboardButton(
                text=f"🏢 {salon['name']} ({salon['city']})",
                callback_data=callback_data
            )
        )

    back_callback = "back_to_masters" if "master" in action else "back_to_main"
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback))
    builder.adjust(1)
    return builder.as_markup()


def get_confirmation_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}_{item_id}")
    )
    builder.adjust(2)
    return builder.as_markup()


def get_statistics_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура статистики"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📊 Общая статистика", callback_data="stats_general"),
        InlineKeyboardButton(text="🏢 По салонам", callback_data="stats_salons"),
        InlineKeyboardButton(text="👤 По мастерам", callback_data="stats_masters"),
        InlineKeyboardButton(text="📈 За период", callback_data="stats_period"),
        InlineKeyboardButton(text="ℹ️ Системная информация", callback_data="system_info"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Расширенная клавиатура настроек"""
    builder = InlineKeyboardBuilder()
    builder.add(
        # Основные настройки
        InlineKeyboardButton(text="🔑 Изменить пароль", callback_data="change_password"),
        InlineKeyboardButton(text="🔄 Обновить данные", callback_data="refresh_data"),

        # Системные функции
        InlineKeyboardButton(text="📋 Системные логи", callback_data="system_logs"),
        InlineKeyboardButton(text="🗑️ Очистить логи", callback_data="clear_logs"),

        # Дополнительные функции
        InlineKeyboardButton(text="💾 Резервные копии", callback_data="backup_data"),
        InlineKeyboardButton(text="📤 Экспорт данных", callback_data="export_data"),

        # Уведомления и информация
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="notification_settings"),
        InlineKeyboardButton(text="ℹ️ О системе", callback_data="system_info"),

        # Назад
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()


def get_back_button(callback_data: str) -> InlineKeyboardMarkup:
    """Простая кнопка Назад"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data))
    return builder.as_markup()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура отмены"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)