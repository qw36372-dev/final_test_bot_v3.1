"""
FSM состояния для прохождения теста (aiogram FSMContext).
"""
from aiogram.fsm.state import State, StatesGroup


class TestStates(StatesGroup):
    """Состояния FSM для теста."""
    
    # Ввод пользовательских данных
    waiting_full_name = State()
    waiting_position = State()
    waiting_department = State()
    
    # Выбор уровня сложности (inline кнопки)
    waiting_difficulty = State()
    
    # Прохождение теста
    answering_question = State()
    
    # Завершение теста
    showing_results = State()
    showing_answers = State()  # Показ правильных ответов (60 сек)
    generating_certificate = State()
    
    # Статистика
    showing_stats = State()
