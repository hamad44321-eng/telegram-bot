import asyncio
import os
from typing import List, Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fastapi import FastAPI, Query
from pydantic import BaseModel
from telethon import TelegramClient, functions

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION", "search_session")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "567809992"))

SEARCH_KEYWORDS_AR = [
    "خليج",
    "سعود",
    "كويت",
    "إمارات",
    "قطر",
    "بحرين",
    "جمال",
    "مكياج",
    "ميكب",
    "ستايل",
    "موضة",
    "حصري",
    "حصريات",
]
SEARCH_KEYWORDS_EN = [
    "gulf",
    "ksa",
    "kuwait",
    "uae",
    "qatar",
    "bahrain",
    "beauty",
    "makeup",
    "style",
    "fashion",
    "exclusive",
]

app = FastAPI(title="Personal TG Channel Finder")
tclient = TelegramClient(SESSION, API_ID, API_HASH)

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()


def _match_score(text: str) -> int:
    if not text:
        return 0
    txt = text.lower()
    score = 0
    for kw in SEARCH_KEYWORDS_AR:
        if kw in txt:
            score += 2
    for kw in SEARCH_KEYWORDS_EN:
        if kw in txt:
            score += 1
    return score


class ChannelOut(BaseModel):
    title: str
    username: Optional[str] = None
    members: Optional[int] = None
    about: Optional[str] = None
    invite_link: Optional[str] = None
    score: int = 0


@app.on_event("startup")
async def _startup():
    await tclient.start()
    asyncio.create_task(dp.start_polling(bot))


@dp.message(F.text.startswith("/start"))
async def start(m: types.Message):
    if m.from_user.id != ALLOWED_USER_ID:
        return await m.answer("⛔️ Private bot. Access denied.")
    await m.answer(
        "Hello Hamad 👋\nUse: /find keyword [country]\nExample: /find جمال السعودية"
    )


@dp.message(F.text.startswith("/find"))
async def find(m: types.Message):
    if m.from_user.id != ALLOWED_USER_ID:
        return await m.answer("⛔️ Private bot. Access denied.")
    parts = m.text.split(maxsplit=2)
    if len(parts) < 2:
        return await m.answer("Format: /find keyword country(optional)")
    query = parts[1]
    country = parts[2] if len(parts) == 3 else ""
    await m.answer("Searching 🔎...")

    data = await _search_logic(f"{query} {country}".strip())
    results = data.get("results", [])

    if not results:
        return await m.answer("No results found.")

    lines = []
    kb = InlineKeyboardBuilder()
    for idx, ch in enumerate(results[:10], start=1):
        title = ch.get("title", "Channel")
        username = ch.get("username")
        members = ch.get("members", "?")
        about = (ch.get("about", "") or "")[:140]
        join_link = (
            f"https://t.me/{username}" if username else ch.get("invite_link", "")
        )
        lines.append(f"{idx}) <b>{title}</b> — {members} members\n{about}")
        if join_link:
            kb.button(text=f"Join: {title}", url=join_link)

    kb.adjust(1)
    await m.answer("\n\n".join(lines), reply_markup=kb.as_markup())


async def _search_logic(query: str):
    res = await tclient(functions.contacts.SearchRequest(q=query, limit=80))
    channels: List[ChannelOut] = []
    for ch in res.chats:
        if getattr(ch, "broadcast", False):
            username = getattr(ch, "username", None)
            full = await tclient.get_entity(ch.id)
            about = getattr(full, "about", None)
            try:
                participants = await tclient.get_participants(full, limit=0)
                members = participants.total
            except Exception:
                members = None
            text_blob = " ".join([ch.title or "", username or "", about or ""])
            score = _match_score(text_blob)
            channels.append(
                ChannelOut(
                    title=ch.title,
                    username=username,
                    members=members,
                    about=about,
                    invite_link=None,
                    score=score,
                )
            )
    channels.sort(key=lambda x: ((x.score or 0), (x.members or 0)), reverse=True)
    return {"results": [c.dict() for c in channels[:20]]}


@app.get("/search")
async def http_search(q: str = Query(..., min_length=2), country: str = ""):
    return await _search_logic(f"{q} {country}".strip())
