from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx


class BackendError(Exception):
    pass


def normalize_lab_identifier(value: str) -> str:
    text = value.strip().lower().replace("_", "-")
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return f"lab-{int(digits):02d}"
    return text


class LmsApiClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _host_port(self) -> str:
        parsed = urlparse(self.base_url)
        host = parsed.hostname or "localhost"
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80
        return f"{host}:{port}"

    def _format_request_error(self, exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            phrase = exc.response.reason_phrase
            return f"HTTP {status} {phrase}"

        if isinstance(exc, httpx.ConnectError):
            return f"connection refused ({self._host_port()})"

        if isinstance(exc, httpx.TimeoutException):
            return f"timeout while connecting to {self._host_port()}"

        if isinstance(exc, httpx.RequestError):
            message = str(exc).strip()
            return message or f"request failed for {self._host_port()}"

        message = str(exc).strip()
        return message or "unknown backend error"

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, headers=self._headers, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise BackendError(self._format_request_error(exc)) from exc

    async def _post_json(self, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=self._headers, json=body or {})
                response.raise_for_status()
                if response.content:
                    return response.json()
                return {"ok": True}
        except Exception as exc:
            raise BackendError(self._format_request_error(exc)) from exc

    async def get_items(self) -> list[dict[str, Any]]:
        data = await self._get_json("/items/")
        if not isinstance(data, list):
            raise BackendError("invalid response format from /items/")
        return [item for item in data if isinstance(item, dict)]

    async def get_learners(self) -> list[dict[str, Any]]:
        data = await self._get_json("/learners/")
        if not isinstance(data, list):
            raise BackendError("invalid response format from /learners/")
        return [row for row in data if isinstance(row, dict)]

    async def get_scores(self, lab: str) -> list[dict[str, Any]]:
        data = await self._get_json("/analytics/scores", params={"lab": normalize_lab_identifier(lab)})
        if not isinstance(data, list):
            raise BackendError("invalid response format from /analytics/scores")
        return [row for row in data if isinstance(row, dict)]

    async def get_pass_rates(self, lab: str) -> list[dict[str, Any]]:
        data = await self._get_json("/analytics/pass-rates", params={"lab": normalize_lab_identifier(lab)})
        if not isinstance(data, list):
            raise BackendError("invalid response format from /analytics/pass-rates")
        return [row for row in data if isinstance(row, dict)]

    async def get_timeline(self, lab: str) -> list[dict[str, Any]]:
        data = await self._get_json("/analytics/timeline", params={"lab": normalize_lab_identifier(lab)})
        if not isinstance(data, list):
            raise BackendError("invalid response format from /analytics/timeline")
        return [row for row in data if isinstance(row, dict)]

    async def get_groups(self, lab: str) -> list[dict[str, Any]]:
        data = await self._get_json("/analytics/groups", params={"lab": normalize_lab_identifier(lab)})
        if not isinstance(data, list):
            raise BackendError("invalid response format from /analytics/groups")
        return [row for row in data if isinstance(row, dict)]

    async def get_top_learners(self, lab: str, limit: int = 10) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 20))
        data = await self._get_json(
            "/analytics/top-learners",
            params={"lab": normalize_lab_identifier(lab), "limit": safe_limit},
        )
        if not isinstance(data, list):
            raise BackendError("invalid response format from /analytics/top-learners")
        return [row for row in data if isinstance(row, dict)]

    async def get_completion_rate(self, lab: str) -> dict[str, Any]:
        data = await self._get_json("/analytics/completion-rate", params={"lab": normalize_lab_identifier(lab)})
        if not isinstance(data, dict):
            raise BackendError("invalid response format from /analytics/completion-rate")
        return data

    async def trigger_sync(self) -> dict[str, Any]:
        data = await self._post_json("/pipeline/sync", {})
        if not isinstance(data, dict):
            return {"ok": True}
        return data

    async def get_labs(self) -> list[dict[str, Any]]:
        items = await self.get_items()
        return [item for item in items if item.get("type") == "lab"]

    async def health_summary(self) -> tuple[bool, int]:
        items = await self.get_items()
        return True, len(items)
