"""
Управление статистикой тестов с SQLite.
Сохранение результатов, отслеживание активности, напоминания.
"""
import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from config.settings import settings
from .models import CurrentTestState

logger = logging.getLogger(__name__)


class StatsManager:
    """Менеджер статистики пользователей."""
    
    DB_PATH = settings.data_dir / "stats.db"
    
    def __init__(self):
        self.db_path = self.DB_PATH
    
    async def init_db(self):
        """Инициализация базы данных."""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица результатов тестов
            await db.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    full_name TEXT,
                    position TEXT,
                    department TEXT,
                    specialization TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    grade TEXT NOT NULL,
                    correct_count INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    elapsed_time TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица последней активности (для напоминаний)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    user_id INTEGER PRIMARY KEY,
                    last_activity TIMESTAMP NOT NULL,
                    test_count INTEGER DEFAULT 0,
                    reminder_sent BOOLEAN DEFAULT 0
                )
            """)
            
            await db.commit()
            logger.info("✅ База данных инициализирована")
    
    async def save_result(self, user_id: int, test_state: CurrentTestState):
        """Сохраняет результат теста."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO test_results (
                    user_id, full_name, position, department,
                    specialization, difficulty, grade,
                    correct_count, total_questions, percentage, elapsed_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                test_state.full_name,
                test_state.position,
                test_state.department,
                test_state.specialization,
                test_state.difficulty.value,
                test_state.grade,
                test_state.correct_count,
                test_state.total_questions,
                test_state.percentage,
                test_state.elapsed_time
            ))
            
            # Обновляем активность
            await db.execute("""
                INSERT OR REPLACE INTO user_activity (user_id, last_activity, test_count, reminder_sent)
                VALUES (
                    ?,
                    ?,
                    COALESCE((SELECT test_count FROM user_activity WHERE user_id = ?), 0) + 1,
                    0
                )
            """, (user_id, datetime.now().isoformat(), user_id))
            
            await db.commit()
            logger.info(f"✅ Результат сохранён для пользователя {user_id}")
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Возвращает статистику пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Общая статистика
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_tests,
                    AVG(percentage) as avg_percentage,
                    MAX(percentage) as best_result,
                    MIN(percentage) as worst_result
                FROM test_results
                WHERE user_id = ?
            """, (user_id,))
            row = await cursor.fetchone()
            
            if not row or row['total_tests'] == 0:
                return {
                    "total_tests": 0,
                    "avg_percentage": 0,
                    "best_result": 0,
                    "worst_result": 0,
                    "recent_tests": []
                }
            
            # Последние 5 тестов
            cursor = await db.execute("""
                SELECT specialization, difficulty, grade, percentage, created_at
                FROM test_results
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 5
            """, (user_id,))
            recent = await cursor.fetchall()
            
            return {
                "total_tests": row['total_tests'],
                "avg_percentage": round(row['avg_percentage'], 1),
                "best_result": round(row['best_result'], 1),
                "worst_result": round(row['worst_result'], 1),
                "recent_tests": [dict(r) for r in recent]
            }
    
    async def update_user_activity(self, user_id: int):
        """
        Обновляет время последней активности пользователя.
        
        ИСПРАВЛЕНО: Переименован метод update_activity -> update_user_activity
        для совместимости с вызовами в specializations/*.py
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_activity (user_id, last_activity, test_count, reminder_sent)
                VALUES (
                    ?,
                    ?,
                    COALESCE((SELECT test_count FROM user_activity WHERE user_id = ?), 0),
                    0
                )
            """, (user_id, datetime.now().isoformat(), user_id))
            await db.commit()
    
    async def get_inactive_users(self, days: int = 7) -> List[int]:
        """
        Возвращает список user_id неактивных пользователей.
        
        Args:
            days: Количество дней неактивности
        
        Returns:
            Список user_id
        """
        threshold = (datetime.now() - timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT user_id
                FROM user_activity
                WHERE last_activity < ?
                AND reminder_sent = 0
            """, (threshold,))
            
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def mark_reminder_sent(self, user_id: int):
        """Отмечает, что напоминание отправлено."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE user_activity
                SET reminder_sent = 1
                WHERE user_id = ?
            """, (user_id,))
            await db.commit()


# Глобальный экземпляр
stats_manager = StatsManager()
