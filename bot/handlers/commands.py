from __future__ import annotations

from bot.config import Settings
from bot.services.lms_api import LmsApiClient
from bot.handlers.core.text import build_help_text


async def handle_start(_: Settings) -> str:
    return (
        "Hello! I am your LMS bot.\n"
        "I can help you inspect the LMS backend and later answer questions in natural language.\n"
        "Use /help to see available commands."
    )


async def handle_help(_: Settings) -> str:
    return build_help_text()


async def handle_health(settings: Settings) -> str:
    client = LmsApiClient(settings.lms_api_base_url, settings.lms_api_key)
    healthy = await client.is_healthy()
    if healthy:
        return "LMS backend is up and reachable."
    return "LMS backend is down or unreachable right now."


async def handle_labs(settings: Settings) -> str:
    client = LmsApiClient(settings.lms_api_base_url, settings.lms_api_key)
    try:
        labs = await client.get_labs()
    except Exception:
        return "Could not fetch labs from the LMS backend."

    if not labs:
        return "No labs found."

    lines: list[str] = ["Available labs:"]
    for index, lab in enumerate(labs, start=1):
        title = str(lab.get("title", "Untitled lab"))
        lines.append(f"{index}. {title}")

    return "\n".join(lines)


async def handle_scores(_: Settings, lab_name: str | None) -> str:
    target = lab_name.strip() if lab_name else "<lab>"
    return f"Scores for {target} are not implemented yet."


async def handle_plain_text(_: Settings, text: str) -> str:
    return (
        "Plain-text intent routing is not implemented yet.\n"
        f"You said: {text}"
    )


async def dispatch_command(settings: Settings, text: str) -> str:
    normalized = text.strip()

    if not normalized:
        return "Please enter a command."

    if normalized.startswith("/start"):
        return await handle_start(settings)

    if normalized.startswith("/help"):
        return await handle_help(settings)

    if normalized.startswith("/health"):
        return await handle_health(settings)

    if normalized.startswith("/labs"):
        return await handle_labs(settings)

    if normalized.startswith("/scores"):
        parts = normalized.split(maxsplit=1)
        lab_name = parts[1] if len(parts) > 1 else None
        return await handle_scores(settings, lab_name)

    return await handle_plain_text(settings, normalized)
