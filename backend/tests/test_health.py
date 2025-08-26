import pytest

@pytest.mark.asyncio
async def test_healthcheck(async_client):
    response = await async_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
