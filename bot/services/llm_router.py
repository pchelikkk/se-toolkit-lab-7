from __future__ import annotations

import json
import sys
from typing import Any

import httpx

from bot.config import Settings
from bot.services.lms_api import BackendError, LmsApiClient


SYSTEM_PROMPT = """
You are an LMS analytics bot for students and instructors.

Rules:
- For factual questions about labs, learners, scores, groups, pass rates, timeline, top learners, completion, or syncing data, use tools.
- Never invent backend data.
- For greetings like "hello", reply warmly and explain what you can do.
- For nonsense like "asdfgh", reply helpfully and suggest a few example questions.
- For ambiguous input like "lab 4", ask a clarifying question about what the user wants to know.
- For comparisons across labs, first inspect the available labs, then call the necessary analytics tools, then compare with numbers.
- Prefer concise answers with concrete numbers.
- When the user asks something like "show me scores for lab 4", convert it to the proper lab identifier format such as lab-04 through tool arguments.
- When answering "which lab has the lowest pass rate", inspect labs, gather pass-rate data, compare numeric averages, and then answer with the worst lab and the numbers.
"""


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "List all LMS items, including labs and tasks.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "List enrolled learners and their groups.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution buckets for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier like lab-04"},
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier like lab-04"},
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get submissions per day for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier like lab-04"},
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group scores and student counts for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier like lab-04"},
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get top learners by average score for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier like lab-04"},
                    "limit": {"type": "integer", "description": "How many learners to return", "default": 5},
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get completion rate for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier like lab-04"},
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Refresh LMS data from autochecker.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

TOOL_NAMES = {tool["function"]["name"] for tool in TOOLS}


class LlmRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.lms = LmsApiClient(settings.lms_api_base_url, settings.lms_api_key)
        self.base_url = settings.llm_api_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_api_model

    async def route(self, user_text: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]

        try:
            for _ in range(10):
                message = await self._chat(messages)
                tool_calls = message.get("tool_calls") or []

                if tool_calls:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": self._message_text(message),
                            "tool_calls": tool_calls,
                        }
                    )

                    tool_results = 0

                    for call in tool_calls:
                        call_id = str(call.get("id") or "")
                        function_data = call.get("function") or {}
                        name = str(function_data.get("name") or "").strip()
                        raw_args = function_data.get("arguments") or "{}"

                        try:
                            args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            args = {}

                        if not name:
                            error_result = {
                                "error": "Malformed tool call: empty tool name",
                                "allowed_tools": sorted(TOOL_NAMES),
                            }
                            print("[tool] Ignoring malformed tool call with empty name", file=sys.stderr)
                            if call_id:
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": call_id,
                                        "content": json.dumps(error_result, ensure_ascii=False),
                                    }
                                )
                                tool_results += 1
                            continue

                        if name not in TOOL_NAMES:
                            error_result = {
                                "error": f"Unknown tool: {name}",
                                "allowed_tools": sorted(TOOL_NAMES),
                            }
                            print(f"[tool] Unknown tool requested: {name}", file=sys.stderr)
                            if call_id:
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": call_id,
                                        "content": json.dumps(error_result, ensure_ascii=False),
                                    }
                                )
                                tool_results += 1
                            continue

                        print(f"[tool] LLM called: {name}({json.dumps(args, ensure_ascii=False)})", file=sys.stderr)
                        result = await self._execute_tool(name, args)
                        print(f"[tool] Result: {self._summarize_result(result)}", file=sys.stderr)

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call_id,
                                "content": json.dumps(result, ensure_ascii=False),
                            }
                        )
                        tool_results += 1

                    if tool_results == 0:
                        messages.append(
                            {
                                "role": "system",
                                "content": (
                                    "Your previous tool call was malformed. "
                                    f"Use only these tools: {', '.join(sorted(TOOL_NAMES))}. "
                                    "If you already have enough facts, answer normally."
                                ),
                            }
                        )
                    else:
                        print(f"[summary] Feeding {tool_results} tool result(s) back to LLM", file=sys.stderr)

                    continue

                text = self._message_text(message).strip()
                if text:
                    return text

                return "I didn't understand that. Ask me about labs, scores, groups, learners, or pass rates."

            return "I couldn't finish the request in time. Please try again with a shorter question."
        except BackendError as exc:
            return f"Backend error: {exc}. Check that the services are running."
        except httpx.HTTPStatusError as exc:
            return f"LLM error: HTTP {exc.response.status_code}. Check the Qwen proxy."
        except Exception as exc:
            return f"LLM error: {exc}"

    async def _chat(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": TOOLS,
                    "tool_choice": "auto",
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> Any:
        if name == "get_items":
            return await self.lms.get_items()
        if name == "get_learners":
            return await self.lms.get_learners()
        if name == "get_scores":
            return await self.lms.get_scores(str(args["lab"]))
        if name == "get_pass_rates":
            return await self.lms.get_pass_rates(str(args["lab"]))
        if name == "get_timeline":
            return await self.lms.get_timeline(str(args["lab"]))
        if name == "get_groups":
            return await self.lms.get_groups(str(args["lab"]))
        if name == "get_top_learners":
            return await self.lms.get_top_learners(str(args["lab"]), int(args.get("limit", 5)))
        if name == "get_completion_rate":
            return await self.lms.get_completion_rate(str(args["lab"]))
        if name == "trigger_sync":
            return await self.lms.trigger_sync()
        raise ValueError(f"Unknown tool: {name}")

    def _message_text(self, message: dict[str, Any]) -> str:
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "\n".join(parts)
        return ""

    def _summarize_result(self, result: Any) -> str:
        if isinstance(result, list):
            return f"{len(result)} item(s)"
        if isinstance(result, dict):
            return f"dict with keys: {', '.join(result.keys())}"
        return str(result)
