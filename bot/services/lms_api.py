from __future__ import annotations

from typing import Any

import httpx


class LmsApiClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def is_healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/items/", headers=self._headers)
                response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def get_items(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self.base_url}/items/", headers=self._headers)
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, list):
            raise ValueError("Expected a list of items from LMS API")

        return [item for item in data if isinstance(item, dict)]

    async def get_labs(self) -> list[dict[str, Any]]:
        items = await self.get_items()
        return [item for item in items if item.get("type") == "lab"]
