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


CONTACT = {
    "name": "Mother",
    "phone": "9876543210",
    "email": "mother@example.com",
    "relationship": "Mother",
    "is_primary": True,
}


@pytest.mark.asyncio
async def test_create_contact(client):
    token = await make_user(client)
    r = await client.post("/api/contacts", json=CONTACT, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Mother"
    assert data["is_primary"] is True
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_contacts(client):
    token = await make_user(client)
    await client.post("/api/contacts", json=CONTACT, headers=auth(token))
    await client.post("/api/contacts", json={
        "name": "Friend", "phone": "9000000001",
        "relationship": "Friend", "is_primary": False
    }, headers=auth(token))
    r = await client.get("/api/contacts", headers=auth(token))
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_duplicate_primary_contact(client):
    token = await make_user(client)
    await client.post("/api/contacts", json=CONTACT, headers=auth(token))
    r = await client.post("/api/contacts", json={**CONTACT, "name": "Sister"}, headers=auth(token))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_update_contact(client):
    token = await make_user(client)
    created = await client.post("/api/contacts", json=CONTACT, headers=auth(token))
    cid = created.json()["id"]
    r = await client.put(f"/api/contacts/{cid}", json={"name": "Maa", "is_active": False}, headers=auth(token))
    assert r.status_code == 200
    assert r.json()["name"] == "Maa"
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_contact(client):
    token = await make_user(client)
    created = await client.post("/api/contacts", json=CONTACT, headers=auth(token))
    cid = created.json()["id"]
    r = await client.delete(f"/api/contacts/{cid}", headers=auth(token))
    assert r.status_code == 204
    r2 = await client.get("/api/contacts", headers=auth(token))
    assert len(r2.json()) == 0


@pytest.mark.asyncio
async def test_contact_requires_phone_or_email(client):
    token = await make_user(client)
    r = await client.post("/api/contacts", json={
        "name": "Nobody", "relationship": "Unknown"
    }, headers=auth(token))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_contact_isolation(client):
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")
    created = await client.post("/api/contacts", json=CONTACT, headers=auth(token_a))
    cid = created.json()["id"]
    r = await client.delete(f"/api/contacts/{cid}", headers=auth(token_b))
    assert r.status_code == 403
