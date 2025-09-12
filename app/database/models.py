from datetime import datetime
from typing import Optional, List
from sqlalchemy import BigInteger, String, Integer, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.database import Base


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Owner(id={self.id}, telegram_id={self.telegram_id})>"


class Salon(Base):
    __tablename__ = "salons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    quota_limit: Mapped[int] = mapped_column(Integer, default=0)
    quota_used: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    masters: Mapped[List["Master"]] = relationship("Master", back_populates="salon", cascade="all, delete-orphan")
    analyses: Mapped[List["Analysis"]] = relationship("Analysis", back_populates="salon")

    @property
    def quota_remaining(self) -> int:
        return max(0, self.quota_limit - self.quota_used)

    def __repr__(self) -> str:
        return f"<Salon(id={self.id}, name='{self.name}', city='{self.city}')>"


class Master(Base):
    __tablename__ = "masters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salon_id: Mapped[int] = mapped_column(Integer, ForeignKey("salons.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    analyses_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    salon: Mapped["Salon"] = relationship("Salon", back_populates="masters")
    analyses: Mapped[List["Analysis"]] = relationship("Analysis", back_populates="master")

    def __repr__(self) -> str:
        return f"<Master(id={self.id}, name='{self.name}', telegram_id={self.telegram_id})>"


class Analysis(Base):
    """Расширенная модель анализа для многоэтапного процесса"""
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_id: Mapped[int] = mapped_column(Integer, ForeignKey("masters.id", ondelete="CASCADE"))
    salon_id: Mapped[int] = mapped_column(Integer, ForeignKey("salons.id", ondelete="CASCADE"))

    # === ФОТОГРАФИИ ===
    # Массивы file_id фотографий для каждой руки
    first_hand_photos: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    second_hand_photos: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    # === ОПРОС МАСТЕРА ===
    # Ответ мастера на 1-шаговый опрос
    survey_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # === РЕЗУЛЬТАТЫ ИИ АНАЛИЗА ===
    # Результат анализа первой руки
    ai_first_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Результат анализа второй руки
    ai_second_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Дневник роста, созданный ИИ
    ai_diary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # === СТАТУС АНАЛИЗА ===
    # started, ready_for_ai, ai_analyzing, ai_completed, completed, disputed, ai_error
    status: Mapped[str] = mapped_column(String(50), default="started")

    # === ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ ===
    # Дополнительные данные (для споров, комментариев и т.д.)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # === ВРЕМЕННЫЕ МЕТКИ ===
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ai_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ai_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    master: Mapped["Master"] = relationship("Master", back_populates="analyses")
    salon: Mapped["Salon"] = relationship("Salon", back_populates="analyses")

    @property
    def total_photos_count(self) -> int:
        """Общее количество фотографий"""
        first_count = len(self.first_hand_photos) if self.first_hand_photos else 0
        second_count = len(self.second_hand_photos) if self.second_hand_photos else 0
        return first_count + second_count

    @property
    def is_photos_complete(self) -> bool:
        """Проверка, что фото обеих рук загружены"""
        has_first = self.first_hand_photos and len(self.first_hand_photos) > 0
        has_second = self.second_hand_photos and len(self.second_hand_photos) > 0
        return has_first and has_second

    @property
    def is_ready_for_ai(self) -> bool:
        """Проверка готовности к ИИ анализу"""
        return (
                self.is_photos_complete and
                self.survey_response and
                len(self.survey_response.strip()) >= 10
        )

    @property
    def analysis_duration(self) -> Optional[int]:
        """Продолжительность анализа в секундах"""
        if self.ai_started_at and self.ai_completed_at:
            return int((self.ai_completed_at - self.ai_started_at).total_seconds())
        return None

    @property
    def status_emoji(self) -> str:
        """Эмоджи для статуса анализа"""
        status_emojis = {
            'started': '🟡',
            'ready_for_ai': '🟠',
            'ai_analyzing': '🔵',
            'ai_completed': '🟢',
            'completed': '✅',
            'disputed': '⚠️',
            'ai_error': '🔴'
        }
        return status_emojis.get(self.status, '❓')

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, master_id={self.master_id}, status='{self.status}')>"


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<SystemLog(id={self.id}, action='{self.action}', user_id={self.user_id})>"


# === ДОПОЛНИТЕЛЬНЫЕ МОДЕЛИ ДЛЯ РАСШИРЕННОГО ФУНКЦИОНАЛА ===

class Manager(Base):
    """Модель управляющих салонов"""
    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salon_id: Mapped[int] = mapped_column(Integer, ForeignKey("salons.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    permissions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Права доступа
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    salon: Mapped["Salon"] = relationship("Salon")

    def __repr__(self) -> str:
        return f"<Manager(id={self.id}, name='{self.name}', salon_id={self.salon_id})>"


class AnalysisReview(Base):
    """Модель для системы оспаривания/проверки анализов"""
    __tablename__ = "analysis_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"))
    reviewer_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # ID проверяющего
    reviewer_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'master', 'manager', 'owner'

    review_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'dispute', 'approval', 'revision'
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, resolved, rejected
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis")

    def __repr__(self) -> str:
        return f"<AnalysisReview(id={self.id}, analysis_id={self.analysis_id}, type='{self.review_type}')>"


class AIProcessingLog(Base):
    """Модель для логирования процессов ИИ анализа"""
    __tablename__ = "ai_processing_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"))

    processing_step: Mapped[str] = mapped_column(String(50), nullable=False)  # 'first_hand', 'second_hand', 'diary'
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 'started', 'completed', 'error'

    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Входные данные
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Результат
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Ошибка, если есть

    processing_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Время обработки в секундах
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Количество токенов (если применимо)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis")

    def __repr__(self) -> str:
        return f"<AIProcessingLog(id={self.id}, analysis_id={self.analysis_id}, step='{self.processing_step}')>"