import os
import asyncio
import logging
from typing import Set

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.filters.command import CommandObject

# --- إعداد اللوج ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
)
log = logging.getLogger(__name__)

# --- متغيرات البيئة ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Env TELEGRAM_BOT_TOKEN is missing")

# ADMIN_IDS = "12345,67890"
def parse_admins(raw: str | None) -> Set[str]:
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip().isdigit()}

ADMIN_IDS: Set[str] = parse_admins(os.getenv("ADMIN_IDS"))

# --- راوتر عام للأوامر الأساسية ---
main_router = Router()

@main_router.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        "👋 Hi! I’m alive on Render.\n"
        "Try: /ping\n"
        f"Bot: @{(await message.bot.me()).username}"
    )
    await message.answer(text)

@main_router.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.answer("pong ✅")

# --- أوامر إدارة الويبهوك ---
webhook_router = Router()

def _is_admin(uid: int) -> bool:
    # لو ADMIN_IDS فاضية، اسمح للجميع (للتجربة). فضّل تضيف آي‑ديك.
    return (not ADMIN_IDS) or (str(uid) in ADMIN_IDS)

@webhook_router.message(Command("webhook_status"))
async def webhook_status(message: types.Message, bot: Bot):
    info = await bot.get_webhook_info()
    if info.url:
        await message.answer(f"🔗 Webhook مفعل:\n{info.url}")
    else:
        await message.answer("ℹ️ لا يوجد Webhook (Polling).")

@webhook_router.message(Command("webhook_off"))
async def webhook_off(message: types.Message, bot: Bot):
    if not _is_admin(message.from_user.id):
        return await message.answer("❌ غير مصرح.")
    await bot.delete_webhook(drop_pending_updates=True)
    await message.answer("✅ تم حذف الـ Webhook. يعمل الآن بالـ polling.")

@webhook_router.message(Command("webhook_on"))
async def webhook_on(message: types.Message, bot: Bot, command: CommandObject):
    if not _is_admin(message.from_user.id):
        return await message.answer("❌ غير مصرح.")
    if not command.args:
        return await message.answer(
            "اكتب الرابط بعد الأمر.\nمثال:\n/webhook_on https://example.com/telegram"
        )
    url = command.args.strip()
    await bot.set_webhook(url, drop_pending_updates=True)
    await message.answer(f"✅ تم تفعيل Webhook:\n{url}")

# --- تشغيل البوت بالـ polling ---
async def main():
    bot = Bot(TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # ضمّن الراوترات
    dp.include_router(main_router)
    dp.include_router(webhook_router)

    log.info("🚀 Starting long polling…")
    # احذف أي ويبهوك عالق قبل البدء
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.me()
    log.info("🤖 Logged in as @%s (id=%s)", me.username, me.id)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
