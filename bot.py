# --- أعلى الملف ---
import os
from aiogram import Router, types, Bot
from aiogram.filters import Command

ADMIN_IDS = set(filter(None, os.getenv("ADMIN_IDS", "").split(",")))  # مثال: "12345,67890"

webhook_router = Router()

@webhook_router.message(Command("webhook_off"))
async def webhook_off(message: types.Message, bot: Bot):
    # السماح فقط للمالك
    if ADMIN_IDS and str(message.from_user.id) not in ADMIN_IDS:
        return await message.answer("❌ غير مصرح.")

    # مسح الويبهوك + حذف الرسائل المعلقة
    await bot.delete_webhook(drop_pending_updates=True)
    await message.answer("✅ تم حذف الـ Webhook. الآن البوت يعمل بالـ polling.")

@webhook_router.message(Command("webhook_status"))
async def webhook_status(message: types.Message, bot: Bot):
    info = await bot.get_webhook_info()
    if info.url:
        await message.answer(f"🔗 Webhook مفعل:\n{info.url}")
    else:
        await message.answer("ℹ️ لا يوجد Webhook مفعل (Polling).")

# --- تحت إنشاء الـ Dispatcher/Router الأساسي عندك ---
# مثال: dp.include_router(webhook_router)
# إذا عندك Router اسمه main_router، لا مشكلة، المهم تضيف:
dp.include_router(webhook_router)
