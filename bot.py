import os
import logging
import asyncio
import json
import time
import requests
from pathlib import Path

from health import start_health_server
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID  = int(os.getenv("ADMIN_ID", "0"))
API_ID    = os.getenv("API_ID", "69b708d53d01cb2096d89700")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN o'rnatilmagan!")

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ─── FSM ──────────────────────────────────────────────────────────────────────
class Form(StatesGroup):
    waiting = State()

# ─── Klaviatura ───────────────────────────────────────────────────────────────
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔎 Qidirish")]],
        resize_keyboard=True,
    )

# ─── API qidiruv ──────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://openbudget.uz/",
    "Origin": "https://openbudget.uz",
}

def search_in_api(last_digits: str) -> list[dict]:
    """
    API ning barcha sahifalarini aylanib, oxirgi raqamlar mos
    keladigan telefon raqamlarni topadi.
    """
    url     = f"https://openbudget.uz/api/v2/info/votes/{API_ID}"
    found   = []
    page    = 0
    errors  = 0

    while True:
        params = {"page": page, "size": 50}
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=(10, 30))

            if resp.status_code in (410, 404, 403):
                logger.error(f"API xato: {resp.status_code}")
                break

            resp.raise_for_status()
            data = resp.json()
            errors = 0

        except requests.exceptions.Timeout:
            logger.warning(f"Sahifa {page}: timeout")
            errors += 1
            if errors >= 3:
                break
            time.sleep(3)
            continue

        except Exception as e:
            logger.error(f"Sahifa {page}: {e}")
            errors += 1
            if errors >= 3:
                break
            time.sleep(3)
            continue

        # Content ajratish
        content = None
        if isinstance(data, dict):
            content = data.get("content") or data.get("data") or data.get("items")
        elif isinstance(data, list):
            content = data

        if not content:
            break  # oxirgi sahifa

        for item in content:
            phone = (
                item.get("phoneNumber")
                or item.get("phone")
                or ""
            )
            date = (
                item.get("voteDate")
                or item.get("date")
                or ""
            )
            if str(phone).endswith(last_digits):
                found.append({"phone": str(phone), "date": str(date)})

        page += 1

    return found

# ─── Handlers ─────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "👋 Assalomu alaykum!\n"
        "OpenBudget ovoz qidiruv boti.\n\n"
        "Telefon raqamning oxirgi raqamlarini yuboring — "
        "ovoz bergan yoki bermaganligini tekshiraman.",
        reply_markup=main_kb(),
    )

@dp.message(F.text == "🔎 Qidirish")
async def ask_phone(msg: types.Message, state: FSMContext):
    await state.set_state(Form.waiting)
    await msg.answer(
        "📱 Telefon raqamning oxirgi raqamlarini yuboring:\n\n"
        "Misol: <code>901234567</code> yoki <code>4567</code>",
        parse_mode="HTML",
    )

@dp.message(Form.waiting)
async def do_search(msg: types.Message, state: FSMContext):
    query = msg.text.strip()
    if not query.isdigit():
        await msg.answer("❌ Faqat raqam yuboring.")
        return

    await state.clear()
    wait = await msg.answer(
        f"🔍 <code>{query}</code> qidirilmoqda...\n"
        f"⏳ API dan tekshirilmoqda, kuting.",
        parse_mode="HTML",
    )

    # API qidiruv (blocking — thread da bajariladi)
    loop    = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, search_in_api, query)

    if not results:
        await wait.edit_text(
            f"❌ <code>{query}</code> bo'yicha ovoz topilmadi.\n\n"
            f"Bu raqam bilan ovoz berilmagan.",
            parse_mode="HTML",
        )
    else:
        lines = [f"✅ <b>{len(results)} ta ovoz topildi</b> (<code>{query}</code>):\n"]
        for r in results:
            lines.append(f"📞 <code>{r['phone']}</code>  🗓 {r['date']}")
        await wait.edit_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=main_kb(),
        )

# ─── Main ─────────────────────────────────────────────────────────────────────
async def main():
    start_health_server()
    logger.info("QuickSearch bot ishga tushdi ✅")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
