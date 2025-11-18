import asyncio
import logging
import os
from typing import List, Set

from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.filters.command import CommandObject

# Telethon للبحث الاختياري
from telethon import TelegramClient, functions
from telethon import types as ttypes  # type: ignore

# -------- إعداد اللوج --------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s:%(message)s"
)
log = logging.getLogger("nud-bot")

# -------- المتغيرات --------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Env TELEGRAM_BOT_TOKEN is missing")

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = os.getenv("TELETHON_SESSION", "search_session.session")
SEARCH_LIMIT = int(os.getenv("SEARCH_LIMIT", "20"))


def parse_admins(raw: str | None) -> Set[str]:
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip().isdigit()}


ADMIN_IDS: Set[str] = parse_admins(os.getenv("ADMIN_IDS"))


def is_admin(uid: int) -> bool:
    return (not ADMIN_IDS) or (str(uid) in ADMIN_IDS)


# -------- Routers --------
main_router = Router()
webhook_router = Router()
search_router = Router()

# Telethon client (اختياري)
telethon_client: TelegramClient | None = None


# ===== أوامر أساسية =====
@main_router.message(Command("start"))
async def cmd_start(message: types.Message):
    me = await message.bot.me()
    await message.answer(
        "👋 Hi! I’m alive on Render.\n"
        "Try: /ping\n"
        "Search: /search كلمات البحث\n"
        f"Bot: @{me.username}"
    )


@main_router.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.answer("pong ✅")


# ===== إدارة الويبهوك (لإلغاء أي ويبهوك عالق) =====
@webhook_router.message(Command("webhook_status"))
async def webhook_status(message: types.Message, bot: Bot):
    info = await bot.get_webhook_info()
    await message.answer(f"🔗 {info.url or 'Polling (no webhook)'}")


@webhook_router.message(Command("webhook_off"))
async def webhook_off(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ غير مصرح.")
    await bot.delete_webhook(drop_pending_updates=True)
    await message.answer("✅ تم حذف الـ Webhook. يعمل الآن بالـ polling.")


# ملاحظة: لم ننفذ Webhook receiver هنا. البوت يعمل بالـ polling وهذا أنسب لـ Render.


# ===== البحث عن القنوات (اختياري عبر Telethon) =====
async def telethon_search_channels(query: str, limit: int) -> List[str]:
    global telethon_client
    if telethon_client is None:
        return ["⚠️ Telethon client غير مهيّأ (API_ID/API_HASH مفقودة)."]

    result = await telethon_client(
        functions.contacts.SearchRequest(q=query, limit=limit)
    )
    lines: List[str] = []
    for chat in result.chats:
        if isinstance(chat, ttypes.Channel):  # type: ignore[attr-defined]
            title = chat.title or "—"
            username = getattr(chat, "username", None)
            link = (
                f"https://t.me/{username}" if username else f"(private / id {chat.id})"
            )
            lines.append(f"• {title}\n   {link}")

    return lines[:limit] if lines else ["لا توجد نتائج مطابقة."]


@search_router.message(Command("search"))
async def cmd_search(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.answer("استخدم:\n/search كلمات البحث")
    query = command.args.strip()
    await message.answer(
        f"🔎 يبحث عن: <b>{query}</b>\n(قد يستغرق ثواني…)", parse_mode=ParseMode.HTML
    )
    try:
        lines = await telethon_search_channels(query, SEARCH_LIMIT)
        await message.answer("\n".join(lines[:20]))
    except Exception as e:
        log.exception("search failed")
        await message.answer(f"❌ فشل البحث: {e}")


# ===== التشغيل =====
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(main_router)
    dp.include_router(webhook_router)
    dp.include_router(search_router)

    # تأكد من إلغاء أي ويبهوك عالق
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.me()
    log.info("🤖 Logged in as @%s (id=%s)", me.username, me.id)

    # Telethon اختياري
    global telethon_client
    if API_ID and API_HASH:
        telethon_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await telethon_client.connect()
        if not await telethon_client.is_user_authorized():
            log.warning(
                "⚠️ Telethon session غير مصادق. استخدمها محليًا لحفظ الجلسة: %s",
                SESSION_NAME,
            )
        else:
            log.info("✅ Telethon جاهز للبحث.")
    else:
        log.warning("⚠️ API_ID/API_HASH غير مضبوطة؛ سيتم تعطيل /search.")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
