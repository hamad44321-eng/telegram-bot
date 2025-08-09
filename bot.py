# bot.py  (Aiogram v3)
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN env var")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(m: Message):
    await m.answer(
        "👋 Hi! I’m alive on Render.\n"
        "Try: /ping\n"
        "Bot: @Nudsie_in_bot"
    )

@dp.message(Command("ping"))
async def cmd_ping(m: Message):
    await m.answer("pong ✅")

@dp.message(F.text)
async def echo(m: Message):
    await m.answer(m.text)

async def main():
    logging.info("🚀 Starting long polling…")
    me = await bot.get_me()
    logging.info("🤖 Logged in as @%s (id=%s)", me.username, me.id)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
