import os
import re
import unicodedata
import asyncio
import logging
from typing import Set, List, Optional

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.client.default import DefaultBotProperties

from telethon import TelegramClient, functions
from telethon.tl import types as ttypes

# ===== Logging =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("channel-search-bot")

# ===== Env =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Env TELEGRAM_BOT_TOKEN is missing")

API_ID = int(os.getenv("API_ID", "0") or "0")
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = os.getenv("TELETHON_SESSION", "search_session.session")
SEARCH_LIMIT = int(os.getenv("SEARCH_LIMIT", "40") or "40")

def parse_ids(raw: Optional[str]) -> Set[str]:
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}

ADMIN_IDS: Set[str] = {x for x in parse_ids(os.getenv("ADMIN_IDS")) if x.isdigit()}

def is_admin(uid: int) -> bool:
    return (not ADMIN_IDS) or (str(uid) in ADMIN_IDS)

# ===== Keyword filter (env‑driven) =====
# ضع كلماتك في KEYWORDS_INCLUDE مفصولة بفواصل (وكذلك KEYWORDS_EXCLUDE إن أردت).
KW_INCLUDE_RAW = os.getenv("# --------- استبدل هذا المقطع فقط في bot.py ---------
# كلمات مطلوبة (مع مرادفات وصيغ قريبة)
WORDS_INCLUDE = [
    # نودز/نودز جميلة/صغيرة
    "نودز", "نودز جميله", "نودز جميلة", "نودز صغيره", "نودز صغيرة",

    # جميلة / صغيره
    "جميله", "جميلة", "صغيره", "صغيرة",

    # حصري / حصريات
    "حصري", "حصريات", "حصريه", "حصريّة", "حصريين",

    # خليجي / خليجية
    "خليجي", "خليجيه", "خليجية", "خليجيين", "خليجيات",

    # سعودي / سعودية / سعوديات
    "سعودي", "سعوديه", "سعودية", "سعوديات",

    # فخم
    "فخم", "فخمه", "فخمة",

    # مكوه (وممكن تكون مقصود بها "مكواة"/"مكوه" بتهجئات)
    "مكوه", "مكواه", "مكواة",

    # تعرض / عرض
    "تعرض", "عرض", "اعلان عرض", "عروض",
]
# -----------------------------------------------------)  # مثال: "سعودي, خليجي, كوميدي"
KW_EXCLUDE_RAW = os.getenv("KEYWORDS_EXCLUDE", "")  # مثال: "اخبار, رياضة"

KEYWORDS_INCLUDE = [k.strip() for k in KW_INCLUDE_RAW.split(",") if k.strip()]
KEYWORDS_EXCLUDE = [k.strip() for k in KW_EXCLUDE_RAW.split(",") if k.strip()]

# ⚠️ تذكير قانوني/أخلاقي:
# لا تستخدم هذه الأداة للبحث عن محتوى غير قانوني أو استغلالي أو يخالف سياسات تيليجرام والقوانين المحلية.
# سَبْقًا: أي كلمات توحي باستغلال قُصَّر أو محتوى غير مشروع = ممنوع تمامًا.

AR_MAP = str.maketrans({
    "أ":"ا","إ":"ا","آ":"ا","ى":"ي","ة":"ه","ؤ":"و","ئ":"ي",
    "٠":"0","١":"1","٢":"2","٣":"3","٤":"4","٥":"5","٦":"6","٧":"7","٨":"8","٩":"9"
})
DIACRITICS = r"[\u0617-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]"

def normalize_ar(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(AR_MAP)
    text = re.sub(DIACRITICS, "", text)
    return text.lower()

def fuzzify(word: str) -> re.Pattern:
    w = re.escape(normalize_ar(word))
    # اسمح بفواصل/رموز بين الحروف لمقاومة التهرّب
    return re.compile(r"".join(ch + r"[\W_]*" for ch in w), re.IGNORECASE)

INC_PATTERNS = [fuzzify(w) for w in KEYWORDS_INCLUDE]
EXC_PATTERNS = [fuzzify(w) for w in KEYWORDS_EXCLUDE]

def match_keywords(text: str) -> bool:
    t = normalize_ar(text)
    if not t:
        return False
    if EXC_PATTERNS and any(p.search(t) for p in EXC_PATTERNS):
        return False
    # إذا ما حددت كلمات إدراج، نرجّع كل شيء
    return (not INC_PATTERNS) or any(p.search(t) for p in INC_PATTERNS)

# ===== Routers =====
main_router = Router()
wh_router = Router()
search_router = Router()

tele_client: Optional[TelegramClient] = None

# ---------- Basic ----------
@main_router.message(Command("start"))
async def cmd_start(m: types.Message):
    me = await m.bot.me()
    await m.answer(
        "👋 Bot is live.\n"
        "• /ping\n"
        "• /search <query>  (search public Telegram channels)\n"
        "• /webhook_status | /webhook_off | /webhook_on <url>\n"
        f"Bot: @{me.username}"
    )

@main_router.message(Command("ping"))
async def cmd_ping(m: types.Message):
    await m.answer("pong ✅")

# ---------- Webhook admin ----------
@wh_router.message(Command("webhook_status"))
async def webhook_status(m: types.Message, bot: Bot):
    info = await bot.get_webhook_info()
    await m.answer(f"🔗 {info.url or 'Polling (no webhook)'}")

@wh_router.message(Command("webhook_off"))
async def webhook_off(m: types.Message, bot: Bot):
    if not is_admin(m.from_user.id):
        return await m.answer("❌ غير مصرح.")
    await bot.delete_webhook(drop_pending_updates=True)
    await m.answer("✅ Webhook OFF → polling.")

@wh_router.message(Command("webhook_on"))
async def webhook_on(m: types.Message, bot: Bot, command: CommandObject):
    if not is_admin(m.from_user.id):
        return await m.answer("❌ غير مصرح.")
    if not command.args:
        return await m.answer("استخدم: /webhook_on https://your-domain/hook")
    url = command.args.strip()
    await bot.set_webhook(url, drop_pending_updates=True)
    await m.answer(f"✅ Webhook ON: {url}")

# ---------- Search ----------
async def telethon_search_channels(query: str, limit: int) -> List[str]:
    global tele_client
    if tele_client is None:
        return ["⚠️ Telethon client غير مهيّأ (API_ID/API_HASH/Session)."]

    res = await tele_client(functions.contacts.SearchRequest(q=query, limit=limit))
    lines: List[str] = []
    for chat in res.chats:
        if isinstance(chat, ttypes.Channel):
            title = chat.title or "-"
            username = getattr(chat, "username", None)
            link = f"https://t.me/{username}" if username else f"(private / id {chat.id})"
            text_for_match = f"{title} {username or ''}"
            if not match_keywords(text_for_match):
                continue
            lines.append(f"• {title}\n   {link}")

    if not lines:
        lines.append("لا توجد نتائج مطابقة.")
    return lines[:limit]

@search_router.message(Command("search"))
async def cmd_search(m: types.Message, command: CommandObject):
    if not command.args:
        return await m.answer("استخدم:\n/search كلمات البحث")

    query = command.args.strip()
    await m.answer(f"🔎 يبحث عن: <b>{query}</b>\n(قد يستغرق ثوانٍ…)", parse_mode="HTML")
    try:
        rows = await telethon_search_channels(query, SEARCH_LIMIT)
        chunk = "\n".join(rows[:30])
        await m.answer(chunk or "لا نتائج.")
    except Exception as e:
        log.exception("search failed")
        await m.answer(f"❌ فشل البحث: {e}")

# ---------- Run ----------
async def main():
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(main_router)
    dp.include_router(wh_router)
    dp.include_router(search_router)

    # تأكد من عدم وجود Webhook عالق
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.me()
    log.info("🤖 Logged in as @%s (id=%s)", me.username, me.id)

    # Telethon init
    global tele_client
    if API_ID and API_HASH:
        tele_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await tele_client.connect()
        if not await tele_client.is_user_authorized():
            log.warning("⚠️ Telethon session غير مصادق. سجّل محليًا وأنسخ %s", SESSION_NAME)
        else:
            log.info("✅ Telethon ready. SEARCH_LIMIT=%d", SEARCH_LIMIT)
    else:
        log.warning("⚠️ API_ID/API_HASH غير مضبوطة؛ سيتم تعطيل /search.")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
