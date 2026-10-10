import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.main import app
from backend.database import Base, get_db

# Use in-memory SQLite for tests
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


@pytest_asyncio.fixture
async def registered_user(client):
    payload = {"full_name": "Test User", "email": "test@safeher.com", "password": "securepass123"}
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    return {"token": resp.json()["access_token"], **payload}


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/api/auth/register", json={
        "full_name": "Priya Sharma",
        "email": "priya@safeher.com",
        "password": "mypassword1",
    })
    assert resp.status_code == 201
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_register_duplicate_email(client, registered_user):
    resp = await client.post("/api/auth/register", json={
        "full_name": "Another User",
        "email": registered_user["email"],
        "password": "anotherpass1",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client):
    resp = await client.post("/api/auth/register", json={
        "full_name": "Weak Pass",
        "email": "weak@safeher.com",
        "password": "123",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client, registered_user):
    resp = await client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client, registered_user):
    resp = await client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    resp = await client.post("/api/auth/login", json={
        "email": "nobody@safeher.com",
        "password": "somepassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client, registered_user):
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == registered_user["email"]
    assert data["full_name"] == registered_user["full_name"]


@pytest.mark.asyncio
async def test_me_no_token(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_user_data_isolation(client):
    """Two users must not be able to access each other's /me data via token swap."""
    await client.post("/api/auth/register", json={
        "full_name": "User One", "email": "one@safeher.com", "password": "password111"
    })
    r2 = await client.post("/api/auth/register", json={
        "full_name": "User Two", "email": "two@safeher.com", "password": "password222"
    })
    token2 = r2.json()["access_token"]

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert me.json()["email"] == "two@safeher.com"
