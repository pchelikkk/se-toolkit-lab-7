from __future__ import annotations

from bot.config import Settings
from bot.handlers.core.text import build_help_text
from bot.services.lms_api import BackendError, LmsApiClient


async def handle_start(_: Settings) -> str:
    return (
        "Welcome to the LMS bot.\n"
        "I can check backend health, list labs, and show pass rates.\n"
        "Use /help to see available commands."
    )


async def handle_help(_: Settings) -> str:
    return build_help_text()


async def handle_health(settings: Settings) -> str:
    client = LmsApiClient(settings.lms_api_base_url, settings.lms_api_key)
    try:
        _, item_count = await client.health_summary()
        return f"Backend is healthy. {item_count} items available."
    except BackendError as exc:
        return f"Backend error: {exc}. Check that the services are running."


async def handle_labs(settings: Settings) -> str:
    client = LmsApiClient(settings.lms_api_base_url, settings.lms_api_key)
    try:
        labs = await client.get_labs()
    except BackendError as exc:
        return f"Backend error: {exc}. Check that the services are running."

    if not labs:
        return "No labs found."

    lines: list[str] = ["Available labs:"]
    for lab in labs:
        title = str(lab.get("title", "Untitled lab"))
        lines.append(f"- {title}")

    return "\n".join(lines)


async def handle_scores(settings: Settings, lab_name: str | None) -> str:
    if not lab_name or not lab_name.strip():
        return "Usage: /scores <lab>. Example: /scores lab-04"

    client = LmsApiClient(settings.lms_api_base_url, settings.lms_api_key)
    target = lab_name.strip().lower()

    try:
        rows = await client.get_pass_rates(target)
    except BackendError as exc:
        return f"Backend error: {exc}. Check that the services are running."

    if not rows:
        return f"No pass-rate data found for {target}."

    lines = [f"Pass rates for {target}:"]
    for row in rows:
        task = str(row.get("task", "Unnamed task"))
        avg_score = float(row.get("avg_score", 0.0))
        attempts = int(row.get("attempts", 0))
        lines.append(f"- {task}: {avg_score:.1f}% ({attempts} attempts)")

    return "\n".join(lines)


async def handle_plain_text(_: Settings, text: str) -> str:
    return (
        "Natural-language routing is not implemented yet.\n"
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

    if normalized.startswith("/"):
        return "Unknown command. Use /help to see available commands."

    return await handle_plain_text(settings, normalized)
