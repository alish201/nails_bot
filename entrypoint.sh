#!/bin/bash
set -e

echo "Starting entrypoint script..."

# Функция для проверки доступности PostgreSQL
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done
    echo "PostgreSQL is up - continuing"
}

# Функция для выполнения миграций
run_migrations() {
    echo "Running database migrations..."

    # Проверяем, существует ли директория migrations
    if [ ! -d "migrations" ]; then
        echo "Migrations directory not found, initializing..."
        alembic init migrations

        # Копируем правильный env.py если он существует
        if [ -f "env.py" ]; then
            cp env.py migrations/env.py
        fi

        # Копируем alembic.ini если он существует
        if [ -f "alembic.ini" ]; then
            cp alembic.ini ./
        fi
    fi

    # Проверяем состояние базы данных
    echo "Checking database state..."

    # Проверяем, есть ли таблица alembic_version
    DB_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT to_regclass('alembic_version');" 2>/dev/null | xargs || echo "")

    if [ "$DB_EXISTS" = "alembic_version" ]; then
        echo "Alembic version table exists, checking current version..."
        CURRENT_VERSION=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null | xargs || echo "")
        echo "Current database version: $CURRENT_VERSION"

        # Если текущая версия - пустая миграция, создаем правильные таблицы
        if [ "$CURRENT_VERSION" = "e7b676d796cf" ]; then
            echo "Found empty initial migration, creating proper initial migration..."

            # Отмечаем базу как не инициализированную
            PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "DELETE FROM alembic_version;"

            # Создаем новую миграцию с реальными таблицами
            alembic revision --autogenerate -m "Create initial tables"
        fi
    else
        echo "Database not initialized with Alembic, will create initial migration..."
    fi

    # Применяем миграции
    echo "Applying migrations..."

    # Попытка применить миграции с обработкой ошибок
    if ! alembic upgrade head; then
        echo "Migration failed, checking if we need to stamp the database..."

        # Если миграция не удалась, возможно нужно проштамповать базу
        echo "Attempting to stamp database with current revision..."
        alembic stamp head

        echo "Retrying migration..."
        alembic upgrade head
    fi

    echo "Migrations completed successfully"
}

# Основная логика
main() {
    echo "DB_HOST: $DB_HOST"
    echo "DB_PORT: $DB_PORT"
    echo "DB_NAME: $DB_NAME"
    echo "DB_USER: $DB_USER"

    # Ждем готовности PostgreSQL
    wait_for_postgres

    # Выполняем миграции
    run_migrations

    # Запускаем переданную команду
    echo "Starting application: $@"
    exec "$@"
}

# Если скрипт запущен напрямую, выполняем основную функцию
if [ "${1#-}" != "$1" ] || [ "${1%.py}" != "$1" ] || [ "$1" = "python" ]; then
    main "$@"
else
    exec "$@"
fi