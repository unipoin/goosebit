from typing import Any

import pytest
from httpx import AsyncClient

from goosebit.db.models import Rollout


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["/api/v1/rollouts", "/ui/bff/rollouts"])
async def test_create_rollout_running_by_default(
    async_client: AsyncClient, test_data: dict[str, Any], url: str
) -> None:
    software = test_data["software_release"]

    response = await async_client.put(url, json={"name": "running", "feed": "default", "software_id": software.id})

    assert response.status_code == 200
    rollout = await Rollout.get(name="running")
    assert rollout.paused is False


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["/api/v1/rollouts", "/ui/bff/rollouts"])
async def test_create_rollout_paused(async_client: AsyncClient, test_data: dict[str, Any], url: str) -> None:
    software = test_data["software_release"]

    response = await async_client.put(
        url, json={"name": "paused", "feed": "default", "software_id": software.id, "paused": True}
    )

    assert response.status_code == 200
    rollout = await Rollout.get(name="paused")
    assert rollout.paused is True
