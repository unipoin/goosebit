from urllib.parse import quote

import pytest
from httpx import AsyncClient

PAYLOAD = '"><img src=x onerror=alert(1)>'


@pytest.mark.asyncio
async def test_logs_page_escapes_device_id(async_client: AsyncClient) -> None:
    response = await async_client.get(f"/ui/logs/{quote(PAYLOAD, safe='')}")

    assert response.status_code == 200
    # the raw payload must never reach the page, neither in HTML nor in the inline script
    assert PAYLOAD not in response.text
    assert "<img src=x" not in response.text


@pytest.mark.asyncio
async def test_nav_permissions_rendered_as_json(async_client: AsyncClient) -> None:
    response = await async_client.get("/ui/devices")

    assert response.status_code == 200
    assert 'const PERMISSIONS = ["*"];' in response.text
