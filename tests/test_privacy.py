import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.main import app
from backend.database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_db] = override_get_db
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def make_user(client, email="user@safeher.com"):
    r = await client.post("/api/auth/register", json={
        "full_name": "Test User", "email": email, "password": "testpass123"
    })
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_default_privacy_settings(client):
    token = await make_user(client)
    r = await client.get("/api/privacy", headers=auth(token))
    assert r.status_code == 200
    data = r.json()
    # All privacy-sensitive features off by default
    assert data["location_access_enabled"] is False
    assert data["location_sharing_enabled"] is False
    assert data["store_journey_location"] is False
    assert data["voice_assistance_enabled"] is False
    assert data["auto_escalate_on_journey_expiry"] is False


@pytest.mark.asyncio
async def test_update_privacy_settings(client):
    token = await make_user(client)
    r = await client.put("/api/privacy", json={
        "location_access_enabled": True,
        "location_sharing_enabled": True,
        "safety_event_retention_days": 7,
    }, headers=auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["location_access_enabled"] is True
    assert data["location_sharing_enabled"] is True
    assert data["safety_event_retention_days"] == 7


@pytest.mark.asyncio
async def test_partial_update(client):
    token = await make_user(client)
    await client.put("/api/privacy", json={"voice_assistance_enabled": True}, headers=auth(token))
    r = await client.get("/api/privacy", headers=auth(token))
    data = r.json()
    assert data["voice_assistance_enabled"] is True
    # Other settings unchanged
    assert data["location_access_enabled"] is False


@pytest.mark.asyncio
async def test_invalid_retention_days(client):
    token = await make_user(client)
    r = await client.put("/api/privacy", json={"safety_event_retention_days": -1}, headers=auth(token))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_empty_voice_phrase(client):
    token = await make_user(client)
    r = await client.put("/api/privacy", json={"voice_trigger_phrase": "   "}, headers=auth(token))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_privacy_summary(client):
    token = await make_user(client)
    r = await client.get("/api/privacy/summary", headers=auth(token))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "data_collected" in data
    assert "data_not_collected" in data
    assert len(data["items"]) == 8


@pytest.mark.asyncio
async def test_privacy_isolation(client):
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")
    await client.put("/api/privacy", json={"voice_assistance_enabled": True}, headers=auth(token_a))
    r = await client.get("/api/privacy", headers=auth(token_b))
    # User B's settings must not be affected by User A's changes
    assert r.json()["voice_assistance_enabled"] is False


@pytest.mark.asyncio
async def test_update_voice_phrase(client):
    token = await make_user(client)
    r = await client.put("/api/privacy", json={"voice_trigger_phrase": "call police"}, headers=auth(token))
    assert r.status_code == 200
    assert r.json()["voice_trigger_phrase"] == "call police"
