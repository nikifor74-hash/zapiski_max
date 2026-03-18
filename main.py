import asyncio
import logging
import signal

from maxapi import Bot, Dispatcher

from config import BOT_TOKEN
from database import Database
from handlers import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    db = Database()
    await db.init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_routers(router)

    await bot.delete_webhook()
    logger.info("Бот запущен, начинаем polling...")

    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Получен сигнал остановки, завершаем работу...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        polling_task = asyncio.create_task(dp.start_polling(bot))
        await stop_event.wait()
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
