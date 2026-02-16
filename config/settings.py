"""
Конфигурация бота: пути, тайминги, токен из окружения.
Production-ready для Bothost.ru: Pydantic v2, обработка ошибок, логирование.
"""
import os
import sys
import logging
from pathlib import Path
from typing import Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки бота с поддержкой Bothost.ru."""
    
    # === КРИТИЧЕСКИЕ ПАРАМЕТРЫ ===
    api_token: str = Field(default="")
    environment: str = Field(default="production")
    
    # === ПУТИ К ФАЙЛАМ И ПАПКАМ ===
    base_dir: Path = Path(__file__).parent.parent
    questions_dir: Path = base_dir / "questions"
    assets_dir: Path = base_dir / "assets"
    data_dir: Path = base_dir / "data"
    logs_dir: Path = base_dir / "logs"
    certs_dir: Path = base_dir / "data" / "certificates"
    
    # === ТАЙМИНГИ УРОВНЕЙ СЛОЖНОСТИ (в минутах) ===
    difficulty_times: Dict[str, int] = {
        "резерв": 35,
        "базовый": 25,
        "стандартный": 20,
        "продвинутый": 20
    }
    
    # === КОЛИЧЕСТВО ВОПРОСОВ ПО УРОВНЯМ ===
    difficulty_questions: Dict[str, int] = {
        "резерв": 20,
        "базовый": 30,
        "стандартный": 40,
        "продвинутый": 50
    }
    
    # === ПОРОГИ ОЦЕНОК (в процентах) ===
    grades: Dict[str, float] = {
        "неудовлетворительно": 59.0,
        "удовлетворительно": 69.0,
        "хорошо": 79.0,
        "отлично": 100.0
    }
    
    # === СПЕЦИАЛИЗАЦИИ ===
    specializations: list[str] = [
        "oupds", "ispolniteli", "aliment", "doznanie", "rozyisk",
        "prof", "oko", "informatika", "kadry", "bezopasnost", "upravlenie"
    ]
    
    # === ПАРАМЕТРЫ ЛОГИРОВАНИЯ И ВЫВОДА ===
    answers_show_time: int = 60
    log_level: str = "INFO"
    use_file_logging: bool = True
    
    model_config = {"case_sensitive": False}
    
    @field_validator("api_token", mode="before")
    @classmethod
    def validate_api_token(cls, v):
        """Валидация API токена с поддержкой переменных окружения."""
        token = v or os.getenv("API_TOKEN", "").strip()
        
        if not token:
            error_msg = (
                "❌ ОШИБКА: API_TOKEN не установлен!\n"
                "Убедитесь, что переменная окружения API_TOKEN установлена"
            )
            print(error_msg, file=sys.stderr)
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError(error_msg)
            logging.warning("API_TOKEN не найден - используется пустой токен (только для разработки)")
        
        return token
    
    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v):
        """Установка окружения из переменной окружения."""
        return (v or os.getenv("ENVIRONMENT", "production")).lower()


# === ИНИЦИАЛИЗАЦИЯ И СОЗДАНИЕ ДИРЕКТОРИЙ ===
settings = Settings()
logger = logging.getLogger(__name__)


def setup_logging():
    """Настройка логирования с поддержкой Bothost.ru."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Базовая конфигурация для консоли (всегда активна)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Логирование в файл (если разрешено и возможно)
    if settings.use_file_logging:
        try:
            settings.logs_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(
                settings.logs_dir / "bot.log",
                encoding="utf-8"
            )
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)
            logger.info("✅ Логирование в файл активировано")
        except (OSError, PermissionError) as e:
            logger.warning(
                f"⚠️ Не удалось создать логирование в файл ({e}). "
                "Используется только консольное логирование."
            )


def ensure_directories_exist():
    """Создание необходимых директорий с обработкой ошибок."""
    required_dirs = [
        (settings.questions_dir, "questions"),
        (settings.assets_dir, "assets"),
        (settings.data_dir, "data"),
        (settings.logs_dir, "logs"),
        (settings.certs_dir, "certificates")
    ]
    
    for dir_path, dir_name in required_dirs:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"✅ Директория {dir_name}: {dir_path}")
        except PermissionError:
            logger.error(
                f"❌ ОШИБКА ПРАВ: Нет доступа к созданию {dir_name} ({dir_path})"
            )
            if settings.environment == "production":
                raise
        except OSError as e:
            logger.error(f"❌ ОШИБКА ОС: Не удалось создать {dir_name} ({dir_path}): {e}")
            if settings.environment == "production":
                raise


def validate_environment():
    """Валидация полной конфигурации перед запуском."""
    logger.info(f"🤖 Запуск в режиме: {settings.environment.upper()}")
    
    # Проверка критических параметров
    if not settings.api_token:
        error_msg = "❌ Критическая ошибка: API_TOKEN не установлен"
        logger.error(error_msg)
        if settings.environment == "production":
            raise ValueError(error_msg)
    
    # Проверка структуры данных
    if len(settings.specializations) != 11:
        logger.warning(
            f"⚠️ Ожидается 11 специализаций, найдено: {len(settings.specializations)}"
        )
    
    logger.info("✅ Конфигурация валидна")


# === ИНИЦИАЛИЗАЦИЯ ПРИ ИМПОРТЕ ===
try:
    setup_logging()
    ensure_directories_exist()
    validate_environment()
    logger.info("✅ Настройки загружены успешно")
except Exception as e:
    logger.critical(f"❌ Критическая ошибка при инициализации: {e}")
    if settings.environment == "production":
        raise
