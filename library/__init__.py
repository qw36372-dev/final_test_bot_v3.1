"""
library/__init__.py: Централизованный экспорт всех модулей библиотеки.
Production-ready для использования в test_bot_main и specializations.
"""

# Базовые модели и enum
from .enum import Difficulty
from .models import Question, CurrentTestState
from .states import TestStates

# Загрузка вопросов
from .question_loader import load_questions_for_specialization

# Таймер
from .timers import TestTimer, create_timer

# Клавиатуры
from .keyboards import (
    get_main_keyboard,
    get_difficulty_keyboard,
    get_test_keyboard,
    get_finish_keyboard
)

# Основная логика
from .library import (
    show_question,
    handle_answer_toggle,
    handle_next_question,
    finish_test
)

# Middlewares
from .middlewares import AntiSpamMiddleware, ErrorHandlerMiddleware

# PDF сертификаты
from .certificates import generate_certificate

# Статистика
from .stats import stats_manager

__all__ = [
    # Enum и модели
    "Difficulty",
    "Question",
    "CurrentTestState",
    "TestStates",
    
    # Загрузка вопросов
    "load_questions_for_specialization",
    
    # Таймер
    "TestTimer",
    "create_timer",
    
    # Клавиатуры
    "get_main_keyboard",
    "get_difficulty_keyboard",
    "get_test_keyboard",
    "get_finish_keyboard",
    
    # Логика теста
    "show_question",
    "handle_answer_toggle",
    "handle_next_question",
    "finish_test",
    
    # Middlewares
    "AntiSpamMiddleware",
    "ErrorHandlerMiddleware",
    
    # PDF и статистика
    "generate_certificate",
    "stats_manager",
]
