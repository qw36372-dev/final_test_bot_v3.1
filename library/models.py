"""
Модели для тестов: Pydantic v2, 4 уровня сложности.
Question: из JSON с динамическим перемешиванием вариантов ответов.
CurrentTestState: toggle-ответы, таймер, результаты, история ответов.
"""
import time
import random
from typing import List, Set, Optional, Dict
from pydantic import BaseModel, Field, field_validator

from .enum import Difficulty


class Question(BaseModel):
    """
    Вопрос из библиотеки с поддержкой перемешивания вариантов.
    
    При каждой загрузке вопроса варианты ответов перемешиваются,
    но правильные индексы автоматически пересчитываются.
    """
    question: str = Field(..., min_length=1, max_length=2000)
    options: List[str] = Field(..., min_length=3, max_length=6)
    correct_answers: Set[int] = Field(..., min_length=1)
    difficulty: Difficulty = Difficulty.BASIC
    
    # Новые поля для перемешивания
    original_options: Optional[List[str]] = None  # Оригинальные варианты
    shuffle_mapping: Optional[List[int]] = None   # Маппинг: новый_индекс -> старый_индекс

    @field_validator('correct_answers', mode='after')
    @classmethod
    def validate_correct(cls, v, info):
        """Валидация правильных ответов (1-based индексы)."""
        options = info.data.get('options', [])
        max_opt = len(options)
        if any(i < 1 or i > max_opt for i in v):
            raise ValueError(f'correct_answers: индексы должны быть в диапазоне 1..{max_opt}')
        return v
    
    def shuffle_options(self) -> None:
        """
        Перемешивает варианты ответов и обновляет правильные индексы.
        
        Алгоритм:
        1. Сохраняем оригинальные варианты
        2. Создаём случайную перестановку индексов
        3. Перемешиваем options по этой перестановке
        4. Пересчитываем correct_answers на новые позиции
        """
        if self.original_options is None:
            # Первое перемешивание - сохраняем оригинал
            self.original_options = self.options.copy()
        
        # Создаём случайную перестановку индексов (0-based)
        indices = list(range(len(self.options)))
        random.shuffle(indices)
        self.shuffle_mapping = indices
        
        # Перемешиваем options
        shuffled_options = [self.options[i] for i in indices]
        
        # Пересчитываем correct_answers (1-based)
        # Старые позиции -> новые позиции
        old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(indices)}
        new_correct = set()
        
        for old_correct_idx in self.correct_answers:
            # Конвертируем 1-based -> 0-based -> перемешиваем -> 1-based
            old_zero_based = old_correct_idx - 1
            new_zero_based = old_to_new[old_zero_based]
            new_correct.add(new_zero_based + 1)
        
        self.options = shuffled_options
        self.correct_answers = new_correct


class CurrentTestState(BaseModel):
    """Состояние текущего теста с полной историей."""
    questions: List[Question]
    current_index: int = 0
    selected_answers: Set[int] = Field(default_factory=set)
    answers_history: Dict[int, Set[int]] = Field(default_factory=dict)
    start_time: float = Field(default_factory=time.time)
    timer_task: Optional[object] = None
    last_message_id: Optional[int] = None
    
    # Данные пользователя
    full_name: str = ""
    position: str = ""
    department: str = ""
    specialization: str = ""
    difficulty: Difficulty = Difficulty.BASIC
    
    # Результаты
    correct_count: int = 0
    total_questions: int = 0
    percentage: float = 0.0
    grade: str = ""
    elapsed_time: str = ""
    
    model_config = {"arbitrary_types_allowed": True}

    @field_validator('current_index', mode='after')
    @classmethod
    def validate_index(cls, v, info):
        """Валидация индекса текущего вопроса."""
        questions = info.data.get('questions', [])
        if questions and (v < 0 or v >= len(questions)):
            raise ValueError(f'current_index должен быть в диапазоне 0..{len(questions)-1}')
        return v
    
    def save_answer(self, question_index: int) -> None:
        """Сохраняет текущие выбранные ответы в историю."""
        self.answers_history[question_index] = self.selected_answers.copy()
    
    def load_answer(self, question_index: int) -> None:
        """Загружает ранее выбранные ответы из истории."""
        if question_index in self.answers_history:
            self.selected_answers = self.answers_history[question_index].copy()
        else:
            self.selected_answers = set()
    
    def calculate_results(self) -> None:
        """
        Вычисляет результаты теста.
        
        Проходит по всем вопросам, сравнивает ответы пользователя
        с правильными и вычисляет процент правильных ответов.
        """
        self.total_questions = len(self.questions)
        self.correct_count = 0
        
        for idx, question in enumerate(self.questions):
            user_answer = self.answers_history.get(idx, set())
            if user_answer == question.correct_answers:
                self.correct_count += 1
        
        # Вычисляем процент
        if self.total_questions > 0:
            self.percentage = (self.correct_count / self.total_questions) * 100
        else:
            self.percentage = 0.0
        
        # Определяем оценку
        if self.percentage >= 90:
            self.grade = "отлично"
        elif self.percentage >= 75:
            self.grade = "хорошо"
        elif self.percentage >= 60:
            self.grade = "удовлетворительно"
        else:
            self.grade = "неудовлетворительно"
        
        # Вычисляем затраченное время
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        self.elapsed_time = f"{minutes:02d}:{seconds:02d}"
