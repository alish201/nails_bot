import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, hashed: str) -> bool:
    """Проверка пароля"""
    try:
        salt, stored_hash = hashed.split(':')
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash == stored_hash
    except ValueError:
        return False


def format_datetime(dt: Optional[datetime]) -> str:
    """Форматирование даты и времени"""
    if dt is None:
        return "Не указано"
    return dt.strftime("%d.%m.%Y %H:%M")


def format_quota_info(used: int, limit: int) -> str:
    """Форматирование информации о квотах"""
    remaining = max(0, limit - used)
    return f"Использовано: {used}/{limit} (осталось: {remaining})"


def escape_markdown(text: str) -> str:
    """Экранирование специальных символов для Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


async def log_user_action(user_id: int, action: str, details: Optional[Dict[str, Any]] = None):
    """Логирование действий пользователя"""
    logger.info(f"User {user_id} performed action: {action}", extra={"details": details})


def generate_analysis_id() -> str:
    """Генерация уникального ID для анализа"""
    return f"ANA_{int(datetime.now().timestamp())}_{secrets.token_hex(4)}"


def validate_telegram_username(username: str) -> bool:
    """Валидация Telegram username"""
    if not username:
        return False
    
    # Убираем @ если есть
    username = username.lstrip('@')
    
    # Проверяем длину (5-32 символа)
    if len(username) < 5 or len(username) > 32:
        return False
    
    # Проверяем символы (только буквы, цифры и подчеркивания)
    if not username.replace('_', '').isalnum():
        return False
    
    # Не должен начинаться с цифры
    if username[0].isdigit():
        return False
    
    return True


def format_user_info(name: str, username: Optional[str] = None, user_id: Optional[int] = None) -> str:
    """Форматирование информации о пользователе"""
    info = name
    if username:
        info += f" (@{username})"
    if user_id:
        info += f" [ID: {user_id}]"
    return info


def calculate_percentage(used: int, total: int) -> float:
    """Вычисление процента использования"""
    if total == 0:
        return 0.0
    return round((used / total) * 100, 2)


def format_statistics(total_analyses: int, total_salons: int, total_masters: int) -> str:
    """Форматирование общей статистики"""
    return (
        f"📊 *Общая статистика:*\n"
        f"🏢 Салонов: {total_salons}\n"
        f"👤 Мастеров: {total_masters}\n"
        f"📸 Анализов: {total_analyses}"
    )
