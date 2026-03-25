from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import get_settings
from bot.handlers.commands import dispatch_command, handle_help, handle_start


async def run_test_mode(text: str) -> int:
    settings = get_settings()
    response = await dispatch_command(settings, text)
    print(response)
    return 0


async def run_telegram_mode() -> int:
    settings = get_settings()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is missing in .env.bot.secret")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start_handler(message: Message) -> None:
        await message.answer(await handle_start(settings))

    @dp.message()
    async def message_handler(message: Message) -> None:
        text = message.text or ""
        if text.strip().startswith("/help"):
            await message.answer(await handle_help(settings))
            return

        response = await dispatch_command(settings, text)
        await message.answer(response)

    await dp.start_polling(bot)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", type=str, help="Run a command in offline test mode")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    if args.test is not None:
        return await run_test_mode(args.test)
    return await run_telegram_mode()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
