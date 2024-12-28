import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from config import API_TOKEN, MONGO_URI
from data.MongoController import MongoController
from handlers.handlers import router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = MongoController(MONGO_URI)

KIEV_TIMEZONE = timezone('Europe/Kiev')

async def reset_daily_report():
    db.reset_daily_report()
    logging.info("Данные отчёта успешно сброшены.")

@router.message.middleware
async def db_middleware(handler, event, data):
    data["db"] = db
    return await handler(event, data)

dp.include_router(router)

async def main():
    logging.info("Бот запущен")
    scheduler = AsyncIOScheduler(timezone=KIEV_TIMEZONE)
    scheduler.add_job(reset_daily_report, CronTrigger(hour=0, minute=0))
    scheduler.start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
