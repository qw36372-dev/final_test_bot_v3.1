"""
Таймер для тестов с async/await и callback при истечении времени.
"""
import asyncio
import logging
import time
from typing import Callable, Awaitable

from .enum import Difficulty
from config.settings import settings

logger = logging.getLogger(__name__)


class TestTimer:
    """Асинхронный таймер для теста."""
    
    def __init__(self, duration_minutes: int, timeout_callback: Callable[[], Awaitable[None]]):
        """
        Инициализация таймера.
        
        Args:
            duration_minutes: Длительность в минутах
            timeout_callback: Асинхронная функция, вызываемая при истечении времени
        """
        self.duration_seconds = duration_minutes * 60
        self.timeout_callback = timeout_callback
        self.start_time: float | None = None
        self.task: asyncio.Task | None = None
        self._cancelled = False
    
    async def _run(self):
        """Внутренний метод запуска таймера."""
        try:
            await asyncio.sleep(self.duration_seconds)
            if not self._cancelled:
                logger.info(f"⏰ Таймер истёк ({self.duration_seconds}s)")
                await self.timeout_callback()
        except asyncio.CancelledError:
            logger.debug("⏰ Таймер отменён")
            raise
    
    async def start(self):
        """Запустить таймер."""
        if self.task is not None:
            logger.warning("⚠️ Таймер уже запущен")
            return
        
        self.start_time = time.time()
        self.task = asyncio.create_task(self._run())
        logger.info(f"▶️ Таймер запущен на {self.duration_seconds // 60} мин")
    
    def stop(self):
        """Остановить таймер."""
        if self.task and not self.task.done():
            self._cancelled = True
            self.task.cancel()
            logger.info("⏸️ Таймер остановлен")
    
    def remaining_time(self) -> str:
        """
        Получить оставшееся время в формате MM:SS.
        
        Returns:
            Строка вида "15:30" или "∞" если таймер не запущен
        """
        if self.start_time is None:
            return "∞"
        
        elapsed = time.time() - self.start_time
        remaining = max(0, self.duration_seconds - elapsed)
        
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        return f"{minutes:02d}:{seconds:02d}"


def create_timer(difficulty: Difficulty, timeout_callback: Callable[[], Awaitable[None]]) -> TestTimer:
    """
    Создать таймер для заданного уровня сложности.
    
    Args:
        difficulty: Уровень сложности теста
        timeout_callback: Функция, вызываемая при истечении времени
    
    Returns:
        Настроенный объект TestTimer
    """
    duration = settings.difficulty_times.get(difficulty.value, 20)
    return TestTimer(duration, timeout_callback)
