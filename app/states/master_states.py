from aiogram.fsm.state import State, StatesGroup


class MasterStates(StatesGroup):
    # === МНОГОЭТАПНЫЙ АНАЛИЗ ===
    # Фотографирование первой руки
    waiting_for_first_hand_photos = State()

    # Фотографирование второй руки
    waiting_for_second_hand_photos = State()

    # Опрос мастера (1 вопрос вместо 13)
    waiting_for_survey_response = State()

    # Готов к ИИ анализу
    ready_for_ai_analysis = State()

    # ИИ анализирует данные
    ai_analyzing = State()

    # Просмотр результатов
    reviewing_results = State()

    # Оспаривание результатов
    disputing_results = State()

    # === ДОПОЛНИТЕЛЬНЫЕ СОСТОЯНИЯ ===
    # Просмотр инструкций
    viewing_instructions = State()

    # Просмотр статистики
    viewing_statistics = State()

    # Редактирование фото (если нужно удалить/заменить)
    editing_first_hand_photos = State()
    editing_second_hand_photos = State()

    # Подтверждение действий
    confirming_action = State()

    # Ожидание администратора (при споре)
    waiting_for_admin_review = State()