import os
import asyncio
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from hydrogram import Client, filters
from hydrogram.types import Message, ChatPermissions

# سيرفر وهمي لإبقاء الخدمة تعمل 24/7 على منصة Render
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Moraqeb Bot is active!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyServer)
    server.serve_forever()

API_ID = int(os.environ.get("TELEGRAM_API_ID", 39120728))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "1deec8393ce5aa05c54c0c7e280377d4")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8782796916:AAEe9YRkzbfm3F5e9rj49iHfDS0wRTnVmmo")

# قائمة الكلمات والعبارات المحظورة الشاملة
BLOCKED_KEYWORDS = [
    "سكس",
    "افلام اباحيه",
    "مؤخره",
    "انيك",
    "عارك",
    "سكليف",
    "سكاليف",
    "صحتي",
    "دخل يومي",
    "دخل خاص",
    "اجازه مرضيه",
    "اجازات مرضيه",
    "تقارير طبيه",
    "تقرير طبي",
    "والاعذار",
    "الاعذار",
    "مناهل",
    "تطلع اجازات",
    "اجازات مرضية",
    "وتقارير طبية",
    "مرافق مريض",
    "مشهد مراجعة",
    "تدليك الجسم",
    "يبغى فلوس",
    "اجازه",
    "تقارير",
    "طبيه",
    "مرضيه",
    "الاجازات"
]

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    # إزالة الحركات والتشكيل
    text = re.sub(r"[\u064B-\u0652]", "", text)
    # توحيد الأحرف المتشابهة
    text = re.sub(r"[أإآ]", "ا", text)
    text = re.sub(r"ة", "ه", text)
    text = re.sub(r"ى", "ي", text)
    return text

NORMALIZED_BLOCKED = [normalize_text(word) for word in BLOCKED_KEYWORDS]

# التعرف على كافة أنواع الروابط
URL_PATTERN = re.compile(r"(https?://\S+|t\.me/\S+|telegram\.me/\S+)", re.IGNORECASE)

async def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()

    bot = Client(
        "moderation_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True
    )

    @bot.on_message(filters.group & ~filters.service)
    async def moderate_messages(client: Client, message: Message):
        if not message.from_user:
            return

        # 1. استثناء المشرفين والمالك
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status.value in ["administrator", "owner"]:
                return
        except Exception:
            pass

        raw_text = message.text or message.caption or ""
        searchable_text = normalize_text(raw_text)

        # 2. فحص وجود روابط أو كلمات محظورة
        has_link = bool(URL_PATTERN.search(raw_text))
        has_blocked_word = any(word in searchable_text for word in NORMALIZED_BLOCKED)

        if has_link or has_blocked_word:
            try:
                # حذف الرسالة المخالفة
                await message.delete()

                # كتم العضو المخالف بالكامل
                await client.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=message.from_user.id,
                    permissions=ChatPermissions()
                )

                # إرسال تنبيه محدد باسم المخالف والسبب
                reason = "إرسال رابط" if has_link else "استخدام كلمات محظورة"
                user_name = message.from_user.first_name or "المستخدم"
                user_mention = message.from_user.mention(user_name)
                
                warning_msg = await client.send_message(
                    chat_id=message.chat.id,
                    text=f"🔇 تم كتم {user_mention} بسبب {reason}."
                )

                # حذف رسالة التنبيه تلقائياً بعد 60 ثانية (دقيقة كاملة)
                await asyncio.sleep(60)
                await warning_msg.delete()

            except Exception as e:
                print(f"❌ تعذر إجراء الكتم: {e}")

    await bot.start()
    print("✅ تم تشغيل بوت المراقب بنجاح.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

