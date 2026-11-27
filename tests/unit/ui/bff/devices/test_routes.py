from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_devices_id_asc(async_client: AsyncClient, test_data: dict[str, Any]) -> None:
    response = await async_client.get("/ui/bff/devices?order[0][dir]=asc&order[0][name]=id")

    assert response.status_code == 200
    devices = response.json()["data"]
    assert len(devices) == 2
    assert devices[0]["id"] == test_data["device_rollout"].id
    assert devices[1]["id"] == test_data["device_assigned"].id


@pytest.mark.asyncio
async def test_list_devices_id_desc(async_client: AsyncClient, test_data: dict[str, Any]) -> None:
    response = await async_client.get("/ui/bff/devices?order[0][dir]=desc&order[0][name]=id")

    assert response.status_code == 200
    devices = response.json()["data"]
    assert len(devices) == 2
    assert devices[0]["id"] == test_data["device_assigned"].id
    assert devices[1]["id"] == test_data["device_rollout"].id


def _target_search(value: str, **extra: Any) -> dict[str, Any]:
    return {
        "columns[0][data]": "assigned_software.version",
        "columns[0][name]": "assigned_software__version",
        "columns[0][search][value]": value,
        **extra,
    }


@pytest.mark.asyncio
async def test_list_devices_target_software_search_includes_rollout(
    async_client: AsyncClient, test_data: dict[str, Any]
) -> None:
    # device1 gets software "1" via rollout, device2 has it assigned; only the latter is stored on the device
    response = await async_client.get("/ui/bff/devices", params=_target_search("1"))

    assert response.status_code == 200
    result = response.json()
    assert result["recordsFiltered"] == 2
    assert {d["id"] for d in result["data"]} == {test_data["device_rollout"].id, test_data["device_assigned"].id}


@pytest.mark.asyncio
async def test_list_devices_target_software_search_no_match(
    async_client: AsyncClient, test_data: dict[str, Any]
) -> None:
    response = await async_client.get("/ui/bff/devices", params=_target_search("rc2"))

    assert response.status_code == 200
    result = response.json()
    assert result["recordsTotal"] == 2
    assert result["recordsFiltered"] == 0
    assert result["data"] == []


@pytest.mark.asyncio
async def test_list_devices_target_software_search_paging(
    async_client: AsyncClient, test_data: dict[str, Any]
) -> None:
    params = _target_search("1", start=1, length=1, **{"order[0][name]": "id", "order[0][dir]": "asc"})
    response = await async_client.get("/ui/bff/devices", params=params)

    assert response.status_code == 200
    result = response.json()
    assert result["recordsFiltered"] == 2
    assert [d["id"] for d in result["data"]] == [test_data["device_assigned"].id]
