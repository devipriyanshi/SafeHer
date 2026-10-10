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


async def make_user(client, email="user@safeher.com", password="testpass123"):
    r = await client.post("/api/auth/register", json={
        "full_name": "Test User", "email": email, "password": password
    })
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


PLAN_PAYLOAD = {
    "name": "College to Home",
    "origin": "LNCT College",
    "destination": "Arera Colony",
    "expected_duration_minutes": 45,
    "notes": "Take bus route 12",
}


@pytest.mark.asyncio
async def test_create_plan(client):
    token = await make_user(client)
    r = await client.post("/api/safety-plans", json=PLAN_PAYLOAD, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "College to Home"
    assert data["expected_duration_minutes"] == 45
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_plans(client):
    token = await make_user(client)
    await client.post("/api/safety-plans", json=PLAN_PAYLOAD, headers=auth(token))
    await client.post("/api/safety-plans", json={**PLAN_PAYLOAD, "name": "Home to Market"}, headers=auth(token))
    r = await client.get("/api/safety-plans", headers=auth(token))
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_get_single_plan(client):
    token = await make_user(client)
    created = await client.post("/api/safety-plans", json=PLAN_PAYLOAD, headers=auth(token))
    plan_id = created.json()["id"]
    r = await client.get(f"/api/safety-plans/{plan_id}", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["id"] == plan_id


@pytest.mark.asyncio
async def test_update_plan(client):
    token = await make_user(client)
    created = await client.post("/api/safety-plans", json=PLAN_PAYLOAD, headers=auth(token))
    plan_id = created.json()["id"]
    r = await client.put(
        f"/api/safety-plans/{plan_id}",
        json={"expected_duration_minutes": 60, "notes": "Updated route"},
        headers=auth(token),
    )
    assert r.status_code == 200
    assert r.json()["expected_duration_minutes"] == 60
    assert r.json()["notes"] == "Updated route"


@pytest.mark.asyncio
async def test_delete_plan(client):
    token = await make_user(client)
    created = await client.post("/api/safety-plans", json=PLAN_PAYLOAD, headers=auth(token))
    plan_id = created.json()["id"]
    r = await client.delete(f"/api/safety-plans/{plan_id}", headers=auth(token))
    assert r.status_code == 204
    r2 = await client.get(f"/api/safety-plans/{plan_id}", headers=auth(token))
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_plan_isolation(client):
    """User A cannot access User B's safety plan."""
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")

    created = await client.post("/api/safety-plans", json=PLAN_PAYLOAD, headers=auth(token_a))
    plan_id = created.json()["id"]

    r = await client.get(f"/api/safety-plans/{plan_id}", headers=auth(token_b))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_plan_isolation_delete(client):
    """User B cannot delete User A's plan."""
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")

    created = await client.post("/api/safety-plans", json=PLAN_PAYLOAD, headers=auth(token_a))
    plan_id = created.json()["id"]

    r = await client.delete(f"/api/safety-plans/{plan_id}", headers=auth(token_b))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_invalid_duration(client):
    token = await make_user(client)
    r = await client.post("/api/safety-plans", json={**PLAN_PAYLOAD, "expected_duration_minutes": 0}, headers=auth(token))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_empty_name(client):
    token = await make_user(client)
    r = await client.post("/api/safety-plans", json={**PLAN_PAYLOAD, "name": "   "}, headers=auth(token))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_unauthenticated_access(client):
    r = await client.get("/api/safety-plans")
    assert r.status_code == 403
