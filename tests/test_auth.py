import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/signals/")
    assert r.status_code == 401
