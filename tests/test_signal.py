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


async def start_journey(client, token):
    r = await client.post("/api/journeys/start", json={
        "origin": "Home", "destination": "Office", "expected_duration_minutes": 30
    }, headers={"Authorization": f"Bearer {token}"})
    return r.json()["id"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_signal(client):
    token = await make_user(client)
    jid = await start_journey(client, token)
    r = await client.post("/api/signals", json={
        "journey_id": jid,
        "signal_type": "manual_check",
        "severity": "low",
        "description": "User manually triggered a safety check.",
    }, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["signal_type"] == "manual_check"
    assert data["source"] == "user"


@pytest.mark.asyncio
async def test_get_journey_signals(client):
    token = await make_user(client)
    jid = await start_journey(client, token)
    for i in range(3):
        await client.post("/api/signals", json={
            "journey_id": jid,
            "signal_type": "manual_check",
            "severity": "low",
            "description": f"Check {i}",
        }, headers=auth(token))
    r = await client.get(f"/api/signals/{jid}", headers=auth(token))
    assert r.status_code == 200
    assert len(r.json()) == 3


@pytest.mark.asyncio
async def test_signal_on_completed_journey_fails(client):
    token = await make_user(client)
    jid = await start_journey(client, token)
    await client.post(f"/api/journeys/{jid}/complete", headers=auth(token))
    r = await client.post("/api/signals", json={
        "journey_id": jid,
        "signal_type": "manual_check",
        "severity": "low",
        "description": "Should fail.",
    }, headers=auth(token))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_signal_isolation(client):
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")
    jid = await start_journey(client, token_a)
    r = await client.post("/api/signals", json={
        "journey_id": jid,
        "signal_type": "manual_check",
        "severity": "low",
        "description": "Unauthorized signal attempt.",
    }, headers=auth(token_b))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_signals_isolation(client):
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")
    jid = await start_journey(client, token_a)
    r = await client.get(f"/api/signals/{jid}", headers=auth(token_b))
    assert r.status_code == 403
