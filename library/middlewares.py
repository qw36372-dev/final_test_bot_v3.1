"""
Middlewares: AntiSpam (flood protect), ErrorHandler.
Для dp.message.middleware() и dp.callback_query.middleware().
"""
import logging
import time
from typing import Dict, Any, Callable, Awaitable
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class AntiSpamMiddleware(BaseMiddleware):
    """
    Защита от спама: ограничение частоты сообщений.
    Лимит: 3 сообщения в секунду на пользователя.
    """
    
    def __init__(self, rate_limit: float = 0.5, max_requests: int = 3):
        """
        Инициализация middleware.
        
        Args:
            rate_limit: Минимальный интервал между сообщениями (секунды)
            max_requests: Максимум запросов за интервал
        """
        super().__init__()
        self.rate_limit = rate_limit
        self.max_requests = max_requests
        self.user_last_time: Dict[int, list[float]] = defaultdict(list)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка события с проверкой на спам."""
        user_id = event.from_user.id
        now = time.time()
        
        # Получаем историю запросов пользователя
        user_times = self.user_last_time[user_id]
        
        # Удаляем старые записи (старше rate_limit)
        user_times[:] = [t for t in user_times if now - t < self.rate_limit]
        
        # Проверяем лимит
        if len(user_times) >= self.max_requests:
            logger.warning(f"⚠️ Спам от пользователя {user_id}")
            
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Слишком частые действия! Подождите немного.", show_alert=True)
            else:
                await event.answer("⏳ Не спамьте! Подождите секунду.")
            
            return
        
        # Добавляем текущее время
        user_times.append(now)
        
        # Продолжаем обработку
        return await handler(event, data)


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Middleware для обработки ошибок в хэндлерах.
    Логирует ошибки и отправляет пользователю понятное сообщение.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка события с перехватом ошибок."""
        try:
            return await handler(event, data)
        
        except Exception as e:
            logger.error(
                f"❌ Ошибка в хэндлере для пользователя {event.from_user.id}: {e}",
                exc_info=True
            )
            
            # Отправляем пользователю сообщение об ошибке
            error_text = "❌ Произошла ошибка. Попробуйте начать заново с /start"
            
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer(error_text, show_alert=True)
                    if event.message:
                        await event.message.answer(error_text)
                else:
                    await event.answer(error_text)
            except Exception as send_error:
                logger.error(f"❌ Не удалось отправить сообщение об ошибке: {send_error}")
            
            # Не пробрасываем ошибку дальше
            return None
