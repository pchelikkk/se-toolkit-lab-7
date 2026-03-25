from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Health", callback_data="health"),
                InlineKeyboardButton(text="Labs", callback_data="labs"),
            ],
            [
                InlineKeyboardButton(text="Worst lab", callback_data="worst_lab"),
                InlineKeyboardButton(text="Help", callback_data="help"),
            ],
        ]
    )
