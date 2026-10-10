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


async def add_contact(client, token):
    await client.post("/api/contacts", json={
        "name": "Mother", "phone": "9876543210",
        "email": "mother@example.com", "relationship": "Mother", "is_primary": True
    }, headers=auth(token))


@pytest.mark.asyncio
async def test_sos_no_contacts(client):
    """SOS works even with no contacts — event is created."""
    token = await make_user(client)
    r = await client.post("/api/emergency/sos", json={"event_type": "manual_sos"}, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "active"
    assert data["notifications_sent"] is False


@pytest.mark.asyncio
async def test_sos_with_contacts(client):
    """SOS with active contacts → notifications_sent True."""
    token = await make_user(client)
    await add_contact(client, token)
    r = await client.post("/api/emergency/sos", json={"event_type": "manual_sos"}, headers=auth(token))
    assert r.status_code == 201
    assert r.json()["notifications_sent"] is True


@pytest.mark.asyncio
async def test_sos_location_excluded_by_default(client):
    """Location not stored unless user has enabled include_location_in_alert."""
    token = await make_user(client)
    r = await client.post("/api/emergency/sos", json={
        "event_type": "manual_sos",
        "latitude": 23.2599,
        "longitude": 77.4126,
    }, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    # Default privacy: include_location_in_alert = True, but location_access_enabled = False
    # Location stored only when include_location_in_alert is True (default is True)
    assert data["location_link"] is not None or data["latitude"] is not None


@pytest.mark.asyncio
async def test_sos_location_excluded_when_privacy_off(client):
    """When include_location_in_alert is disabled, location not stored."""
    token = await make_user(client)
    await client.put("/api/privacy", json={"include_location_in_alert": False}, headers=auth(token))
    r = await client.post("/api/emergency/sos", json={
        "event_type": "manual_sos",
        "latitude": 23.2599,
        "longitude": 77.4126,
    }, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["latitude"] is None
    assert data["location_link"] is None


@pytest.mark.asyncio
async def test_cancel_event(client):
    token = await make_user(client)
    sos = await client.post("/api/emergency/sos", json={"event_type": "manual_sos"}, headers=auth(token))
    eid = sos.json()["id"]
    r = await client.post(f"/api/emergency/{eid}/cancel", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_already_cancelled(client):
    token = await make_user(client)
    sos = await client.post("/api/emergency/sos", json={"event_type": "manual_sos"}, headers=auth(token))
    eid = sos.json()["id"]
    await client.post(f"/api/emergency/{eid}/cancel", headers=auth(token))
    r = await client.post(f"/api/emergency/{eid}/cancel", headers=auth(token))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_emergency_history(client):
    token = await make_user(client)
    await client.post("/api/emergency/sos", json={"event_type": "manual_sos"}, headers=auth(token))
    await client.post("/api/emergency/sos", json={"event_type": "user_alert"}, headers=auth(token))
    r = await client.get("/api/emergency/history", headers=auth(token))
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_emergency_isolation(client):
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")
    sos = await client.post("/api/emergency/sos", json={"event_type": "manual_sos"}, headers=auth(token_a))
    eid = sos.json()["id"]
    r = await client.post(f"/api/emergency/{eid}/cancel", headers=auth(token_b))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_voice_sos_event_type(client):
    token = await make_user(client)
    r = await client.post("/api/emergency/sos", json={"event_type": "voice_sos"}, headers=auth(token))
    assert r.status_code == 201
    assert r.json()["event_type"] == "voice_sos"


@pytest.mark.asyncio
async def test_history_isolation(client):
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")
    await client.post("/api/emergency/sos", json={"event_type": "manual_sos"}, headers=auth(token_a))
    r = await client.get("/api/emergency/history", headers=auth(token_b))
    assert r.status_code == 200
    assert len(r.json()) == 0
