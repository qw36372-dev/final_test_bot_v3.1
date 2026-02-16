"""
Загрузка вопросов из JSON файлов специализаций.
Поддержка вложенной структуры папок + перемешивание вариантов ответов.
"""
import json
import logging
import random
from pathlib import Path
from typing import List

from config.settings import settings
from .models import Question
from .enum import Difficulty

logger = logging.getLogger(__name__)


def load_questions_for_specialization(
    specialization: str,
    difficulty: Difficulty,
    user_id: int | None = None
) -> List[Question]:
    """
    Загружает вопросы для специализации/сложности.
    
    Поддерживает 3 формата файлов (по приоритету):
    1. Вложенная структура: questions/{specialization}/{difficulty}.json
    2. Плоская с суффиксом: questions/{specialization}_{difficulty}.json
    3. Общий файл: questions/{specialization}.json
    
    Args:
        specialization: Название специализации (oupds, aliment, и т.д.)
        difficulty: Уровень сложности
        user_id: ID пользователя для seed (optional)
    
    Returns:
        Список объектов Question с перемешанными вариантами ответов
    """
    # Маппинг сложности (русский → английский для имён файлов)
    difficulty_map = {
        "резерв": "reserve",
        "базовый": "basic", 
        "стандартный": "standard",
        "продвинутый": "advanced"
    }
    
    difficulty_name = difficulty_map.get(difficulty.value, "basic")
    
    # Попытка 1: Вложенная структура (РЕКОМЕНДУЕТСЯ)
    nested_path = settings.questions_dir / specialization / f"{difficulty_name}.json"
    
    # Попытка 2: Плоская с суффиксом
    flat_with_suffix = settings.questions_dir / f"{specialization}_{difficulty_name}.json"
    
    # Попытка 3: Общий файл
    general_path = settings.questions_dir / f"{specialization}.json"
    
    # Выбираем путь (по приоритету)
    if nested_path.exists():
        json_path = nested_path
        logger.info(f"📂 Используется вложенная структура: {specialization}/{difficulty_name}.json")
    elif flat_with_suffix.exists():
        json_path = flat_with_suffix
        logger.info(f"📂 Используется плоский формат: {specialization}_{difficulty_name}.json")
    elif general_path.exists():
        json_path = general_path
        logger.info(f"📂 Используется общий файл: {specialization}.json")
    else:
        logger.error(f"❌ Файл вопросов не найден для {specialization} ({difficulty_name})")
        return []
    
    try:
        with json_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except (json.JSONDecodeError, PermissionError) as e:
        logger.error(f"❌ Ошибка чтения JSON {json_path}: {e}")
        return []
    
    if not isinstance(raw_data, list):
        logger.error(f"❌ Неверный формат JSON {json_path}: ожидается список")
        return []
    
    # Парсинг вопросов
    questions = []
    for idx, item in enumerate(raw_data):
        try:
            opts = item.get("options", [])
            if not isinstance(opts, list) or len(opts) < 3:
                logger.warning(f"⚠️ Пропуск вопроса {specialization}:{idx} - недостаточно вариантов")
                continue
            
            # Парсинг правильных ответов (строка "1,3,4" -> set{1,3,4})
            correct_str = item.get("correct_answers", "")
            correct = set()
            for x in correct_str.split(","):
                x = x.strip()
                if x.isdigit():
                    correct.add(int(x))
            
            if not correct:
                logger.warning(f"⚠️ Пропуск вопроса {specialization}:{idx} - нет правильных ответов")
                continue
            
            q = Question(
                question=item["question"],
                options=opts,
                correct_answers=correct,
                difficulty=difficulty
            )
            
            # ✅ Перемешиваем варианты ответов для каждого вопроса
            q.shuffle_options()
            
            questions.append(q)
            
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"⚠️ Пропуск вопроса {specialization}:{idx}: {e}")
            continue
    
    if not questions:
        logger.error(f"❌ Не удалось загрузить вопросы для {specialization}")
        return []
    
    # Количество вопросов для данного уровня сложности
    target_count = settings.difficulty_questions.get(difficulty.value, 30)
    
    # Random shuffle с user_seed для честности
    if user_id:
        random.seed(user_id)
    random.shuffle(questions)
    random.seed()  # Сброс seed
    
    # Выбор нужного количества вопросов
    if len(questions) < target_count:
        logger.warning(
            f"⚠️ Мало вопросов {specialization}: {len(questions)} < {target_count}. "
            f"Используем все доступные."
        )
        selected = questions
    else:
        selected = questions[:target_count]
    
    logger.info(
        f"✅ Загружено {len(selected)} вопросов для {specialization} "
        f"({difficulty.value}) с перемешанными вариантами"
    )
    
    return selected
