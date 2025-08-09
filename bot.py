import os
import asyncio
import logging
from typing import Set, List

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.client.default import DefaultBotProperties

# Telethon للبحث العام
from telethon import TelegramClient, functions, types as ttypes

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
)
log = logging.getLogger("nud-bot")

# ---------- Envs ----------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Env TELEGRAM_BOT_TOKEN is missing")

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = os.getenv("TELETHON_SESSION", "search_session.session")
SEARCH_LIMIT = int(os.getenv("SEARCH_LIMIT", "20"))

# كلمات افتراضيّة من env (مفصولة بفواصل)
KEYWORDS_INCLUDE = os.getenv("KEYWORDS_INCLUDE", "").strip()

def parse_admins(raw: str | None) -> Set[str]:
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip().isdigit()}

ADMIN_IDS: Set[str] = parse_admins(os.getenv("ADMIN_IDS"))

def is_admin(uid: int) -> bool:
    return (not ADMIN_IDS) or (str(uid) in ADMIN_IDS)

# ---------- Routers ----------
main_router = Router()
webhook_router = Router()
search_router = Router()

# عميل Telethon
telethon_client: TelegramClient | None = None

# ---------- أوامر أساسية ----------
@main_router.message(Command("start"))
async def cmd_start(message: types.Message):
    me = await message.bot.me()
    await message.answer(
        "👋 Hi! I’m alive on Render.\n"
        "• /ping — اختبار سريع\n"
        "• /search كلمات… — بحث قنوات\n"
        "• /keywords — عرض كلمات البحث الافتراضيّة\n"
        f"Bot: @{me.username}"
    )

@main_router.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.answer("pong ✅")

@main_router.message(Command("keywords"))
async def cmd_keywords(message: types.Message):
    if KEYWORDS_INCLUDE:
        await message.answer(f"📎 الكلمات الافتراضيّة:\n{KEYWORDS_INCLUDE}")
    else:
        await message.answer("ℹ️ لا توجد كلمات افتراضيّة (KEYWORDS_INCLUDE فارغة).")

# ---------- ويبهوك إدارة ----------
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

@webhook_router.message(Command("webhook_on"))
async def webhook_on(message: types.Message, bot: Bot, command: CommandObject):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ غير مصرح.")
    if not command.args:
        return await message.answer("أرسل الرابط بعد الأمر: /webhook_on https://example.com/hook")
    url = command.args.strip()
    await bot.set_webhook(url, drop_pending_updates=True)
    await message.answer(f"✅ Webhook ON: {url}")

# ---------- البحث ----------
async def telethon_search_channels(query: str, limit: int) -> List[str]:
    """يرجع أسطر نصيّة عن القنوات المطابقة (الاسم + رابط)."""
    global telethon_client
    if telethon_client is None:
        return ["⚠️ Telethon client غير مهيّأ (راجع API_ID/API_HASH)."]

    res = await telethon_client(functions.contacts.SearchRequest(q=query, limit=limit))
    lines: List[str] = []
    for chat in res.chats:
        if isinstance(chat, ttypes.Channel):
            title = chat.title or "—"
            username = getattr(chat, "username", None)
            link = f"https://t.me/{username}" if username else f"(private / id {chat.id})"
            lines.append(f"• {title}\n   {link}")

    if not lines:
        lines.append("لا توجد نتائج مطابقة.")
    return lines[:limit]

@search_router.message(Command("search"))
async def cmd_search(message: types.Message, command: CommandObject):
    # لو ما فيه Args، استخدم KEYWORDS_INCLUDE من env
    query = (command.args or "").strip()
    if not query:
        if not KEYWORDS_INCLUDE:
            return await message.answer("استخدم:\n/search كلمات البحث\nأو ضَع KEYWORDS_INCLUDE في متغيّرات البيئة.")
        query = KEYWORDS_INCLUDE

    await message.answer(f"🔎 يبحث عن:\n<b>{query}</b>\n(قد يستغرق بضع ثواني…)", parse_mode="HTML")
    try:
        lines = await telethon_search_channels(query, SEARCH_LIMIT)
        # لا نخلي الرسالة طويلة جدًا
        chunk = "\n".join(lines[:20])
        await message.answer(chunk)
    except Exception as e:
        log.exception("search failed")
        await message.answer(f"❌ فشل البحث: {e}")

# ---------- التشغيل ----------
async def main():
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(main_router)
    dp.include_router(webhook_router)
    dp.include_router(search_router)

    # تأكد من إلغاء أي ويبهوك
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.me()
    log.info("🤖 Logged in as @%s (id=%s)", me.username, me.id)

    # Telethon
    global telethon_client
    if API_ID and API_HASH:
        telethon_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await telethon_client.connect()
        if not await telethon_client.is_user_authorized():
            log.warning("⚠️ Telethon session غير مصادق. سجّل الدخول محليًا واحفظ الجلسة: %s", SESSION_NAME)
        else:
            log.info("✅ Telethon جاهز للبحث.")
    else:
        log.warning("⚠️ API_ID/API_HASH غير مضبوطة؛ سيتم تعطيل /search.")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
