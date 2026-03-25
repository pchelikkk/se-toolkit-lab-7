from __future__ import annotations


def build_help_text() -> str:
    return (
        "Available commands:\n"
        "/start - show welcome message\n"
        "/help - show this help\n"
        "/health - check LMS backend status\n"
        "/labs - list available labs\n"
        "/scores <lab> - show scores for a lab (placeholder for now)"
    )
