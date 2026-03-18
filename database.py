import logging

import aiosqlite

from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Database:
    """Асинхронная работа с SQLite через aiosqlite."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Создаёт таблицу tasks, если её нет."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_text TEXT NOT NULL,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'done')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    list_name TEXT DEFAULT 'main',
                    due_date TIMESTAMP
                )
            ''')
            await db.commit()
            logger.info("База данных инициализирована")

    async def add_task(self, user_id: int, task_text: str, list_name: str = 'main'):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (user_id, task_text, list_name) VALUES (?, ?, ?)",
                (user_id, task_text, list_name)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_pending_tasks(self, user_id: int, list_name: str = 'main'):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, task_text FROM tasks WHERE user_id = ? AND status = 'pending' AND list_name = ? ORDER BY created_at",
                (user_id, list_name)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_task_done(self, task_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE tasks SET status = 'done' WHERE id = ? AND user_id = ? AND status = 'pending'",
                (task_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0
