"""
Клавиатуры: главное меню, уровни сложности, тест с ЧИСЛОВЫМИ кнопками 1️⃣2️⃣3️⃣4️⃣5️⃣, результаты.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .enum import Difficulty


# Маппинг цифр на эмодзи
NUMBER_EMOJI = {
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣"
}


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню: 11 специализаций inline кнопками В ОДНУ КОЛОНКУ."""
    builder = InlineKeyboardBuilder()
    
    # 11 специализаций - ПОЛНЫЕ названия в одну колонку
    specs = [
        ("🚨 ООУПДС", "spec_oupds"),
        ("📊 Исполнительное производство", "spec_ispolniteli"),
        ("🧑‍🧑‍🧒 Алименты", "spec_aliment"),
        ("🎯 Дознание", "spec_doznanie"),
        ("⏳ Исполнительный розыск и реализация имущества", "spec_rozyisk"),
        ("📈 Организация профессиональной подготовки", "spec_prof"),
        ("📡 Организация управления и контроля", "spec_oko"),
        ("💻 Информатизация и информационная безопасность", "spec_informatika"),
        ("👥 Кадровая работа", "spec_kadry"),
        ("🔒 Обеспечение собственной безопасности", "spec_bezopasnost"),
        ("💼 Управленческая деятельность", "spec_upravlenie"),
    ]
    
    for text, callback in specs:
        builder.button(text=text, callback_data=callback)
    
    builder.button(text="❓ Помощь 🆘", callback_data="help")
    
    # ВСЁ В ОДНУ КОЛОНКУ!
    builder.adjust(1)
    
    return builder.as_markup()


def get_difficulty_keyboard() -> InlineKeyboardMarkup:
    """Выбор уровня сложности."""
    builder = InlineKeyboardBuilder()
    
    difficulties = [
        ("🥉 Резерв (20 вопросов, 35 мин)", "diff_резерв"),
        ("🥈 Базовый (30 вопросов, 25 мин)", "diff_базовый"),
        ("🥇 Стандартный (40 вопросов, 20 мин)", "diff_стандартный"),
        ("💎 Продвинутый (50 вопросов, 20 мин)", "diff_продвинутый"),
    ]
    
    for text, callback in difficulties:
        builder.button(text=text, callback_data=callback)
    
    builder.adjust(1)  # 1 колонка
    return builder.as_markup()


def get_test_keyboard(num_options: int, selected: set[int] | None = None) -> InlineKeyboardMarkup:
    """
    Клавиатура теста ТОЛЬКО с числовыми эмодзи 1️⃣2️⃣3️⃣4️⃣5️⃣.
    Варианты ответов показываются в тексте сообщения!
    
    Args:
        num_options: Количество вариантов ответа
        selected: Множество выбранных номеров (1-based)
    
    Returns:
        InlineKeyboardMarkup только с числовыми кнопками
    """
    builder = InlineKeyboardBuilder()
    selected = selected or set()
    
    # Создаем кнопки ТОЛЬКО с эмодзи (без текста вариантов!)
    for i in range(1, num_options + 1):
        # Числовой эмодзи
        number_emoji = NUMBER_EMOJI.get(i, str(i))
        
        # Галочка если выбрано
        check = "✅ " if i in selected else ""
        
        # Текст кнопки - ТОЛЬКО эмодзи и галочка
        button_text = f"{check}{number_emoji}"
        
        builder.button(
            text=button_text,
            callback_data=f"ans_{i}"
        )
    
    # Кнопка "Далее"
    builder.button(text="➡️ Далее", callback_data="next")
    
    # Компоновка: все кнопки в один ряд (или несколько рядов по 5)
    if num_options <= 5:
        builder.adjust(num_options, 1)  # Все варианты в 1 ряд + Далее отдельно
    else:
        builder.adjust(5, num_options - 5, 1)  # Первые 5 в ряд, остальные ниже
    
    return builder.as_markup()


def get_finish_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после завершения теста."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📋 Показать правильные ответы", callback_data="show_answers")
    builder.button(text="🏆 Сертификат PDF", callback_data="generate_cert")
    builder.button(text="🔄 Повторить тест", callback_data="repeat_test")
    builder.button(text="📊 Моя статистика", callback_data="my_stats")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    
    builder.adjust(1)  # 1 колонка
    return builder.as_markup()
