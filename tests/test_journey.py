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


JOURNEY_PAYLOAD = {
    "origin": "LNCT College",
    "destination": "Arera Colony",
    "expected_duration_minutes": 45,
}


@pytest.mark.asyncio
async def test_start_journey(client):
    token = await make_user(client)
    r = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "active"
    assert data["origin"] == "LNCT College"
    assert data["extension_count"] == 0


@pytest.mark.asyncio
async def test_only_one_active_journey(client):
    token = await make_user(client)
    await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    r = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_get_active_journey(client):
    token = await make_user(client)
    await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    r = await client.get("/api/journeys/active", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["status"] == "active"


@pytest.mark.asyncio
async def test_no_active_journey_returns_null(client):
    token = await make_user(client)
    r = await client.get("/api/journeys/active", headers=auth(token))
    assert r.status_code == 200
    assert r.json() is None


@pytest.mark.asyncio
async def test_mark_safe(client):
    token = await make_user(client)
    started = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    jid = started.json()["id"]
    r = await client.post(f"/api/journeys/{jid}/safe", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["status"] == "active"


@pytest.mark.asyncio
async def test_extend_journey(client):
    token = await make_user(client)
    started = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    jid = started.json()["id"]
    r = await client.post(f"/api/journeys/{jid}/extend", json={"extend_by_minutes": 15}, headers=auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["expected_duration_minutes"] == 60
    assert data["extension_count"] == 1


@pytest.mark.asyncio
async def test_complete_journey(client):
    token = await make_user(client)
    started = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    jid = started.json()["id"]
    r = await client.post(f"/api/journeys/{jid}/complete", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_cancel_journey(client):
    token = await make_user(client)
    started = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    jid = started.json()["id"]
    r = await client.post(f"/api/journeys/{jid}/cancel", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_action_on_completed_journey_fails(client):
    token = await make_user(client)
    started = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    jid = started.json()["id"]
    await client.post(f"/api/journeys/{jid}/complete", headers=auth(token))
    r = await client.post(f"/api/journeys/{jid}/extend", json={"extend_by_minutes": 10}, headers=auth(token))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_journey_isolation(client):
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")
    started = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token_a))
    jid = started.json()["id"]
    r = await client.post(f"/api/journeys/{jid}/complete", headers=auth(token_b))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_journey_timeline(client):
    token = await make_user(client)
    started = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    jid = started.json()["id"]
    await client.post(f"/api/journeys/{jid}/safe", headers=auth(token))
    await client.post(f"/api/journeys/{jid}/complete", headers=auth(token))

    r = await client.get(f"/api/journeys/{jid}/timeline", headers=auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    events = [e["event"] for e in data["timeline"]]
    assert "Journey Started" in events
    assert "Journey Completed" in events


@pytest.mark.asyncio
async def test_journey_expiry(client):
    """Simulate expiry by directly calling the service with a backdated journey."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from backend.models.journey import SafetyJourney, JourneyStatus
    from backend.services.journey_service import check_and_expire_journeys

    token = await make_user(client)
    started = await client.post("/api/journeys/start", json=JOURNEY_PAYLOAD, headers=auth(token))
    jid = started.json()["id"]

    # Backdate expected_arrival_at so it appears overdue
    async with TestSession() as db:
        result = await db.execute(select(SafetyJourney).where(SafetyJourney.id == jid))
        journey = result.scalar_one()
        journey.expected_arrival_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        await db.commit()

    async with TestSession() as db:
        expired = await check_and_expire_journeys(db)
        assert jid in expired

    r = await client.get(f"/api/journeys/{jid}", headers=auth(token))
    assert r.json()["status"] == "expired"
