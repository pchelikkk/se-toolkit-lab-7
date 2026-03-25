from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import get_settings
from bot.handlers.commands import dispatch_command, handle_help, handle_start
from bot.keyboards import build_start_keyboard
from bot.services.llm_router import LlmRouter


async def run_test_mode(text: str) -> int:
    settings = get_settings()

    if text.strip().startswith("/"):
        response = await dispatch_command(settings, text)
    else:
        router = LlmRouter(settings)
        response = await router.route(text)

    print(response)
    return 0


async def run_telegram_mode() -> int:
    settings = get_settings()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is missing in .env.bot.secret")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    llm_router = LlmRouter(settings)

    @dp.message(CommandStart())
    async def start_handler(message: Message) -> None:
        await message.answer(await handle_start(settings), reply_markup=build_start_keyboard())

    @dp.callback_query()
    async def callback_handler(callback: CallbackQuery) -> None:
        data = callback.data or ""

        if data == "help":
            response = await handle_help(settings)
        elif data == "health":
            response = await dispatch_command(settings, "/health")
        elif data == "labs":
            response = await dispatch_command(settings, "/labs")
        elif data == "worst_lab":
            response = await llm_router.route("which lab has the lowest pass rate?")
        else:
            response = "Unknown action."

        if callback.message:
            await callback.message.answer(response, reply_markup=build_start_keyboard())
        await callback.answer()

    @dp.message()
    async def message_handler(message: Message) -> None:
        text = (message.text or "").strip()
        if not text:
            await message.answer("Please send text or use a button.")
            return

        if text.startswith("/"):
            response = await dispatch_command(settings, text)
        else:
            response = await llm_router.route(text)

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
