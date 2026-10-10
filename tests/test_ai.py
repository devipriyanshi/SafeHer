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
async def test_analyze_clean_journey(client):
    """Journey with no signals → normal indication."""
    token = await make_user(client)
    jid = await start_journey(client, token)
    r = await client.post("/api/ai/analyze", json={"journey_id": jid}, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["indication"] == "normal"
    assert 0 <= data["assistance_score"] <= 30
    assert data["suggested_action"] != ""
    assert data["explanation"] != ""


@pytest.mark.asyncio
async def test_analyze_returns_valid_indication(client):
    """Indication must be one of the three valid values."""
    token = await make_user(client)
    jid = await start_journey(client, token)
    r = await client.post("/api/ai/analyze", json={"journey_id": jid}, headers=auth(token))
    assert r.json()["indication"] in ("normal", "attention_recommended", "potentially_unusual")


@pytest.mark.asyncio
async def test_analyze_with_signals(client):
    """Adding delay + expiry signals should raise indication."""
    token = await make_user(client)
    jid = await start_journey(client, token)

    for sig_type in ["journey_delay", "journey_expired", "route_deviation"]:
        await client.post("/api/signals", json={
            "journey_id": jid,
            "signal_type": sig_type,
            "severity": "medium",
            "description": f"Test signal: {sig_type}",
        }, headers=auth(token))

    r = await client.post("/api/ai/analyze", json={"journey_id": jid}, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["indication"] in ("attention_recommended", "potentially_unusual")
    assert data["assistance_score"] > 30


@pytest.mark.asyncio
async def test_get_latest_assessment(client):
    token = await make_user(client)
    jid = await start_journey(client, token)
    await client.post("/api/ai/analyze", json={"journey_id": jid}, headers=auth(token))
    r = await client.get(f"/api/ai/assessment/{jid}", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["journey_id"] == jid


@pytest.mark.asyncio
async def test_no_assessment_returns_null(client):
    token = await make_user(client)
    jid = await start_journey(client, token)
    r = await client.get(f"/api/ai/assessment/{jid}", headers=auth(token))
    assert r.status_code == 200
    assert r.json() is None


@pytest.mark.asyncio
async def test_ai_assessment_isolation(client):
    token_a = await make_user(client, "a@safeher.com")
    token_b = await make_user(client, "b@safeher.com")
    jid = await start_journey(client, token_a)
    r = await client.post("/api/ai/analyze", json={"journey_id": jid}, headers=auth(token_b))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_ai_fallback_when_model_missing(client):
    """If model file is absent, predictor returns safe fallback — not an error."""
    import pathlib
    from backend.ai_safety import predictor as pred_module

    original = pred_module.MODEL_PATH
    pred_module.MODEL_PATH = pathlib.Path("nonexistent_model.pkl")
    pred_module._artifact = None  # reset cache

    token = await make_user(client)
    jid = await start_journey(client, token)
    r = await client.post("/api/ai/analyze", json={"journey_id": jid}, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["ai_available"] is False
    assert data["indication"] == "normal"

    # Restore
    pred_module.MODEL_PATH = original
    pred_module._artifact = None


@pytest.mark.asyncio
async def test_feature_extraction_directly():
    """Unit test feature extractor without HTTP."""
    from backend.ai_safety.features import extract_features, FEATURE_NAMES
    from backend.models.signal import SafetySignal, SignalType, SignalSeverity

    signals = [
        SafetySignal(signal_type=SignalType.JOURNEY_DELAY, severity=SignalSeverity.LOW,
                     journey_id=1, user_id=1, description="delay", source="engine"),
        SafetySignal(signal_type=SignalType.JOURNEY_EXPIRED, severity=SignalSeverity.MEDIUM,
                     journey_id=1, user_id=1, description="expired", source="engine"),
    ]
    features = extract_features(signals, extension_count=1)
    assert features["journey_delay"] == 1
    assert features["journey_expired"] == 1
    assert features["extension_count"] == 1
    assert set(features.keys()) == set(FEATURE_NAMES)


@pytest.mark.asyncio
async def test_score_range_normal():
    from backend.ai_safety.predictor import _compute_score
    score = _compute_score({
        "journey_delay": 0, "route_deviation": 0, "repeated_warnings": 0,
        "manual_checks": 0, "user_triggered": 0, "journey_expired": 0,
        "high_severity_count": 0, "extension_count": 0,
    }, "normal")
    assert 0 <= score <= 30


@pytest.mark.asyncio
async def test_score_range_attention():
    from backend.ai_safety.predictor import _compute_score
    score = _compute_score({
        "journey_delay": 1, "route_deviation": 1, "repeated_warnings": 1,
        "manual_checks": 0, "user_triggered": 0, "journey_expired": 1,
        "high_severity_count": 0, "extension_count": 0,
    }, "attention_recommended")
    assert 31 <= score <= 60
