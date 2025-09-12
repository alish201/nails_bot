from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    # === АВТОРИЗАЦИЯ ===
    waiting_for_password = State()

    # === УПРАВЛЕНИЕ САЛОНАМИ ===
    waiting_for_salon_name = State()
    waiting_for_salon_city = State()
    waiting_for_salon_quota = State()

    # Редактирование салонов
    waiting_for_salon_new_name = State()
    waiting_for_salon_new_city = State()
    waiting_for_salon_new_quota = State()

    # === УПРАВЛЕНИЕ МАСТЕРАМИ ===
    waiting_for_master_name = State()
    waiting_for_master_telegram = State()
    waiting_for_master_salon = State()

    # Редактирование мастеров
    waiting_for_master_new_name = State()
    waiting_for_master_new_telegram = State()
    waiting_for_master_new_salon = State()

    # === ПОПОЛНЕНИЕ КВОТ ===
    waiting_for_quota_salon = State()
    waiting_for_quota_amount = State()

    # === СМЕНА ПАРОЛЯ ===
    waiting_for_current_password = State()
    waiting_for_new_password = State()
    waiting_for_password_confirmation = State()

    # === ПОИСК ===
    waiting_for_search_query = State()
    waiting_for_salon_search = State()
    waiting_for_master_search = State()
    waiting_for_analysis_search = State()

    # === МАССОВЫЕ ОПЕРАЦИИ ===
    waiting_for_bulk_quota_amount = State()
    waiting_for_bulk_notification_text = State()
    selecting_bulk_targets = State()

    # === ЭКСПОРТ ДАННЫХ ===
    configuring_export_options = State()
    waiting_for_export_period_start = State()
    waiting_for_export_period_end = State()
    waiting_for_export_filename = State()

    # === УВЕДОМЛЕНИЯ ===
    configuring_notification_settings = State()
    waiting_for_notification_threshold = State()
    waiting_for_notification_schedule = State()

    # === РЕЗЕРВНЫЕ КОПИИ ===
    creating_backup = State()
    restoring_backup = State()
    waiting_for_backup_name = State()

    # === СИСТЕМА ===
    maintenance_mode = State()
    system_diagnostics = State()

    # === ФИЛЬТРЫ И СОРТИРОВКА ===
    configuring_filter = State()
    waiting_for_filter_value = State()

    # === ОТЧЕТЫ ===
    generating_report = State()
    waiting_for_report_parameters = State()
    waiting_for_report_period = State()

    # === НАСТРОЙКИ АВТОМАТИЗАЦИИ ===
    configuring_auto_quota = State()
    waiting_for_auto_quota_threshold = State()
    waiting_for_auto_quota_amount = State()

    # === ПАГИНАЦИЯ ===
    waiting_for_page_number = State()

    # === ИМПОРТ ДАННЫХ ===
    importing_data = State()
    waiting_for_import_file = State()
    configuring_import_options = State()

    # === СИСТЕМНЫЕ НАСТРОЙКИ ===
    configuring_system_settings = State()
    waiting_for_setting_value = State()

    # === ЛОГИ И МОНИТОРИНГ ===
    viewing_logs = State()
    configuring_log_level = State()
    setting_log_retention = State()

    # === ИНТЕГРАЦИИ ===
    configuring_api_integration = State()
    waiting_for_api_key = State()
    testing_integration = State()

    # === ПОЛЬЗОВАТЕЛЬСКИЕ РОЛИ (для будущих версий) ===
    managing_roles = State()
    creating_role = State()
    editing_permissions = State()