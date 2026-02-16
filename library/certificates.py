"""
Генерация красивых корпоративных PDF сертификатов.
Дизайн: строгий, профессиональный, с официальным гербом ФССП.
"""
import io
import logging
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image

from config.settings import settings
from .models import CurrentTestState

logger = logging.getLogger(__name__)

# Загрузка встроенного шрифта
FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
EMBLEM_PATH = Path(__file__).parent / "static" / "fssp_emblem_opt.png"

def register_fonts():
    """Регистрация русских шрифтов для PDF."""
    try:
        if FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont('DejaVu', str(FONT_PATH)))
            logger.info(f"✅ Шрифт загружен: {FONT_PATH}")
            return 'DejaVu'
        else:
            logger.warning(f"⚠️ Шрифт не найден: {FONT_PATH}, используется Helvetica")
            return 'Helvetica'
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки шрифта: {e}")
        return 'Helvetica'


def draw_decorative_border(c, width, height):
    """Рисует декоративную рамку сертификата."""
    # Внешняя рамка - тёмно-синяя
    c.setStrokeColor(colors.HexColor("#1a5490"))
    c.setLineWidth(3)
    c.rect(30, 30, width - 60, height - 60)
    
    # Внутренняя рамка - светло-синяя
    c.setStrokeColor(colors.HexColor("#4a90d9"))
    c.setLineWidth(1.5)
    c.rect(40, 40, width - 80, height - 80)
    
    # Углы - золотистые акценты
    corner_size = 15
    c.setStrokeColor(colors.HexColor("#d4af37"))
    c.setLineWidth(2)
    
    # Левый верхний
    c.line(40, height - 40, 40 + corner_size, height - 40)
    c.line(40, height - 40, 40, height - 40 - corner_size)
    
    # Правый верхний  
    c.line(width - 40, height - 40, width - 40 - corner_size, height - 40)
    c.line(width - 40, height - 40, width - 40, height - 40 - corner_size)
    
    # Левый нижний
    c.line(40, 40, 40 + corner_size, 40)
    c.line(40, 40, 40, 40 + corner_size)
    
    # Правый нижний
    c.line(width - 40, 40, width - 40 - corner_size, 40)
    c.line(width - 40, 40, width - 40, 40 + corner_size)


def draw_fssp_emblem(c, width, height):
    """Рисует официальный герб ФССП в верхней части."""
    if not EMBLEM_PATH.exists():
        logger.warning(f"⚠️ Герб не найден: {EMBLEM_PATH}")
        return
    
    try:
        # Размер герба (80x80 пикселей)
        emblem_size = 80
        center_x = width / 2
        top_y = height - 120
        
        # Позиция (центрируем)
        x = center_x - emblem_size / 2
        y = top_y - emblem_size / 2
        
        # Рисуем герб
        c.drawImage(
            str(EMBLEM_PATH),
            x, y,
            width=emblem_size,
            height=emblem_size,
            preserveAspectRatio=True,
            mask='auto'
        )
        logger.debug("✅ Герб ФССП отрисован")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отрисовки герба: {e}")


async def generate_certificate(test_state: CurrentTestState, user_id: int) -> io.BytesIO:
    """
    Генерирует красивый корпоративный PDF сертификат с гербом ФССП.
    
    Returns:
        io.BytesIO: PDF в памяти
    """
    font = register_fonts()
    
    # Создаём PDF в памяти
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # === ФОН ===
    # Светло-голубой градиент (имитация)
    c.setFillColor(colors.HexColor("#f0f8ff"))
    c.rect(0, 0, width, height, fill=1, stroke=0)
    
    # Декоративная рамка
    draw_decorative_border(c, width, height)
    
    # Официальный герб ФССП
    draw_fssp_emblem(c, width, height)
    
    # === ЗАГОЛОВОК ===
    c.setFont(font, 32)
    c.setFillColor(colors.HexColor("#1a5490"))
    c.drawCentredString(width / 2, height - 200, "СЕРТИФИКАТ")
    
    # Подзаголовок
    c.setFont(font, 14)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawCentredString(width / 2, height - 225, "о прохождении профессионального тестирования")
    
    # Разделительная линия
    c.setStrokeColor(colors.HexColor("#d4af37"))
    c.setLineWidth(2)
    c.line(150, height - 240, width - 150, height - 240)
    
    # === ДАННЫЕ СОТРУДНИКА ===
    y_pos = height - 280
    left_margin = 100
    
    data_fields = [
        ("ФИО:", test_state.full_name),
        ("Должность:", test_state.position),
        ("Подразделение:", test_state.department),
    ]
    
    c.setFont(font, 11)
    for label, value in data_fields:
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(left_margin, y_pos, label)
        
        c.setFont(font, 11)
        c.setFillColor(colors.black)
        c.drawString(left_margin + 120, y_pos, value)
        
        c.setFont(font, 11)
        y_pos -= 25
    
    # Разделитель
    y_pos -= 10
    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.setLineWidth(1)
    c.line(100, y_pos, width - 100, y_pos)
    y_pos -= 30
    
    # === РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ===
    c.setFont(font, 13)
    c.setFillColor(colors.HexColor("#1a5490"))
    c.drawCentredString(width / 2, y_pos, "РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    y_pos -= 30
    
    test_data = [
        ("Специализация:", test_state.specialization.upper()),
        ("Уровень сложности:", test_state.difficulty.value.capitalize()),
        ("", ""),
        ("Оценка:", test_state.grade.upper()),
        ("Правильных ответов:", f"{test_state.correct_count} из {test_state.total_questions}"),
        ("Результат:", f"{test_state.percentage:.1f}%"),
        ("Затрачено времени:", test_state.elapsed_time),
    ]
    
    c.setFont(font, 10)
    for label, value in test_data:
        if label:
            c.setFillColor(colors.HexColor("#555555"))
            c.drawString(left_margin, y_pos, label)
            
            # Цвет оценки
            if label == "Оценка:":
                if "ОТЛИЧНО" in value:
                    color = colors.HexColor("#2d8c2d")
                elif "ХОРОШО" in value:
                    color = colors.HexColor("#5a9fd4")
                elif "УДОВЛЕТВОРИТЕЛЬНО" in value:
                    color = colors.HexColor("#f39c12")
                else:
                    color = colors.HexColor("#c0392b")
                c.setFillColor(color)
                c.setFont(font, 12)
            else:
                c.setFillColor(colors.black)
                c.setFont(font, 10)
            
            c.drawString(left_margin + 150, y_pos, value)
            c.setFont(font, 10)
        y_pos -= 22
    
    # === ПОДВАЛ ===
    footer_y = 120
    
    # Линия подписи
    c.setStrokeColor(colors.HexColor("#1a5490"))
    c.setLineWidth(1)
    signature_line_width = 200
    signature_x = width / 2 - signature_line_width / 2
    c.line(signature_x, footer_y, signature_x + signature_line_width, footer_y)
    
    # Текст подписи
    c.setFont(font, 8)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawCentredString(width / 2, footer_y - 15, "ФССП РОССИИ")
    c.drawCentredString(width / 2, footer_y - 27, "Система тестирования профессиональной подготовки")
    
    # Дата и ID
    c.setFont(font, 8)
    c.setFillColor(colors.HexColor("#999999"))
    date_str = datetime.now().strftime("%d.%m.%Y")
    c.drawString(80, 50, f"Дата выдачи: {date_str}")
    c.drawRightString(width - 80, 50, f"ID: {user_id}")
    
    # Telegram Bot метка
    c.setFont(font, 7)
    c.setFillColor(colors.HexColor("#cccccc"))
    c.drawCentredString(width / 2, 30, "Telegram Bot")
    
    c.save()
    
    # Возвращаем buffer с позицией в начале
    buffer.seek(0)
    logger.info(f"✅ Сертификат сгенерирован для пользователя {user_id}")
    return buffer
