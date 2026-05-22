import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
dp = Dispatcher()
web_app_url = ""


def load_config():
    load_dotenv(BASE_DIR / ".env")

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    mini_app_url = os.getenv("WEB_APP_URL", "").strip()
    errors = []

    if not bot_token:
        errors.append("BOT_TOKEN not found. Add BOT_TOKEN=YOUR_NEW_BOT_TOKEN to Backend/.env")

    if not mini_app_url:
        errors.append("WEB_APP_URL not found. Add WEB_APP_URL=https://https://tricky-corners-sit.loca.lt to Backend/.env")
    else:
        parsed_url = urlparse(mini_app_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            errors.append("WEB_APP_URL must be a valid HTTPS URL. Use ngrok for local testing.")

    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)

    return bot_token, mini_app_url


@dp.message(CommandStart())
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍔 Открыть меню",
                    web_app=WebAppInfo(url=web_app_url),
                )
            ]
        ]
    )
    await message.answer(
        "Добро пожаловать в FastFood Mini App! Нажмите кнопку ниже, чтобы открыть меню.",
        reply_markup=keyboard,
    )


async def main():
    global web_app_url

    bot_token, web_app_url = load_config()
    bot = Bot(token=bot_token)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
