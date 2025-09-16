# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директорию для логов
RUN mkdir -p logs

# Создаем entrypoint script для миграций
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Устанавливаем переменную окружения для Python
ENV PYTHONPATH=/app

# Expose порт (если нужен)
EXPOSE 8000

# Используем entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# Команда по умолчанию
CMD ["python", "main.py"]