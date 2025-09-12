"""Add extended analysis functionality

Revision ID: 002_extended_analysis
Revises: 001_initial_tables
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_extended_analysis'
down_revision: Union[str, None] = 'e7b676d796cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновление схемы базы данных"""

    # Создание новой таблицы managers (управляющие)
    op.create_table(
        'managers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(length=255), nullable=True),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_managers_telegram_id'), 'managers', ['telegram_id'], unique=True)

    # Создание таблицы analysis_reviews (система оспаривания)
    op.create_table(
        'analysis_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.BigInteger(), nullable=True),
        sa.Column('reviewer_type', sa.String(length=20), nullable=False),
        sa.Column('review_type', sa.String(length=20), nullable=False),
        sa.Column('review_reason', sa.Text(), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Создание таблицы ai_processing_logs (логи ИИ)
    op.create_table(
        'ai_processing_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_id', sa.Integer(), nullable=False),
        sa.Column('processing_step', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_time', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Расширение таблицы analyses новыми полями

    # Добавляем новые JSON поля для фотографий
    op.add_column('analyses', sa.Column('first_hand_photos', sa.JSON(), nullable=True))
    op.add_column('analyses', sa.Column('second_hand_photos', sa.JSON(), nullable=True))

    # Добавляем поле для ответа на опрос
    op.add_column('analyses', sa.Column('survey_response', sa.Text(), nullable=True))

    # Добавляем поля для результатов ИИ анализа
    op.add_column('analyses', sa.Column('ai_first_analysis', sa.JSON(), nullable=True))
    op.add_column('analyses', sa.Column('ai_second_analysis', sa.JSON(), nullable=True))
    op.add_column('analyses', sa.Column('ai_diary', sa.JSON(), nullable=True))

    # Добавляем новые временные метки
    op.add_column('analyses', sa.Column('ai_started_at', sa.DateTime(), nullable=True))
    op.add_column('analyses', sa.Column('ai_completed_at', sa.DateTime(), nullable=True))

    # Обновляем существующие записи - устанавливаем пустые массивы для фото
    op.execute("UPDATE analyses SET first_hand_photos = '[]'::json WHERE first_hand_photos IS NULL")
    op.execute("UPDATE analyses SET second_hand_photos = '[]'::json WHERE second_hand_photos IS NULL")

    # Мигрируем существующие данные photo_file_id в first_hand_photos
    op.execute("""
        UPDATE analyses 
        SET first_hand_photos = json_build_array(photo_file_id)::json
        WHERE photo_file_id IS NOT NULL AND photo_file_id != ''
    """)

    # Добавляем индексы для оптимизации
    op.create_index('ix_analyses_status', 'analyses', ['status'])
    op.create_index('ix_analyses_ai_started_at', 'analyses', ['ai_started_at'])
    op.create_index('ix_analysis_reviews_analysis_id', 'analysis_reviews', ['analysis_id'])
    op.create_index('ix_analysis_reviews_status', 'analysis_reviews', ['status'])
    op.create_index('ix_ai_processing_logs_analysis_id', 'ai_processing_logs', ['analysis_id'])
    op.create_index('ix_ai_processing_logs_processing_step', 'ai_processing_logs', ['processing_step'])


def downgrade() -> None:
    """Откат миграции"""

    # Удаляем индексы
    op.drop_index('ix_ai_processing_logs_processing_step')
    op.drop_index('ix_ai_processing_logs_analysis_id')
    op.drop_index('ix_analysis_reviews_status')
    op.drop_index('ix_analysis_reviews_analysis_id')
    op.drop_index('ix_analyses_ai_started_at')
    op.drop_index('ix_analyses_status')

    # Удаляем новые столбцы из analyses
    op.drop_column('analyses', 'ai_completed_at')
    op.drop_column('analyses', 'ai_started_at')
    op.drop_column('analyses', 'ai_diary')
    op.drop_column('analyses', 'ai_second_analysis')
    op.drop_column('analyses', 'ai_first_analysis')
    op.drop_column('analyses', 'survey_response')
    op.drop_column('analyses', 'second_hand_photos')
    op.drop_column('analyses', 'first_hand_photos')

    # Удаляем новые таблицы
    op.drop_table('ai_processing_logs')
    op.drop_table('analysis_reviews')
    op.drop_index(op.f('ix_managers_telegram_id'), table_name='managers')
    op.drop_table('managers')