from __future__ import annotations


def build_help_text() -> str:
    return (
        "Available commands:\n"
        "/start - show welcome message\n"
        "/help - show this help\n"
        "/health - check LMS backend status and item count\n"
        "/labs - list available labs from the LMS backend\n"
        "/scores <lab> - show per-task pass rates for a lab"
    )
