# SafeHer — Proactive, Privacy-Aware Women Safety Platform

> **SafeHer is an assistive safety platform. It does not guarantee protection, predict crime, or replace emergency services (112). Always contact local emergency services in a genuine emergency.**

---

## Problem Statement

Traditional women safety applications are primarily **reactive** — they wait for an emergency to occur before taking action (SOS → GPS → Alert). They offer little control over privacy, no proactive journey planning, and no explanation of why an alert was triggered.

## Proposed Solution

SafeHer shifts the focus from reaction to **proactive safety management**:

```
Safety Planning → Journey Setup → Privacy-Controlled Monitoring
      → Safety Signal Analysis → Explainable AI Assistance
            → User Decision → Optional Escalation
```

The user remains in control at every step. AI assists — it never decides.

---

## What Makes SafeHer Different

| Traditional Apps | SafeHer |
|---|---|
| SOS → GPS → Alert | Safety Plan → Journey → Signals → AI → User Decision |
| Always tracking | Permission-based, minimum data |
| AI triggers alerts | User triggers alerts |
| No explanation | Explainable AI indication |
| No journey lifecycle | Full journey lifecycle with timeline |
| Privacy as afterthought | Privacy as core feature |

---

## Unique Features

### 1. Safety Planning
Create reusable journey profiles (e.g. "College → Home, 45 min") before travelling.

### 2. Safety Journey Engine
Full journey lifecycle: `ACTIVE → COMPLETED / CANCELLED / EXPIRED`
- Mark Safe, Extend, Complete, Cancel
- Expired journey ≠ danger (user is prompted, not auto-alerted)

### 3. Privacy Center
User controls:
- When location is accessed and shared
- Whether journey location is stored
- What data is included in alerts
- How long events are retained
- All sensitive features **off by default**

### 4. Safety Signal Engine
Structured safety events (journey delay, route deviation, manual check, expiry) feed into AI — they do not trigger alerts directly.

### 5. Explainable AI Safety Assistance
Decision Tree model produces one of three indications:
- `Normal` (score 0–30)
- `Attention Recommended` (score 31–60)
- `Potentially Unusual` (score 61–100)

Every indication includes a written explanation and suggested action. The AI never automatically triggers an emergency.

### 6. Safety Timeline
Chronological record of every event during a journey — start, signals, safe confirmations, completion.

### 7. User-Controlled Escalation
```
AI Indication → User Notification → User Decision → Optional SOS
```
Auto-escalation only if user explicitly enables it in Privacy settings.

### 8. Modular Emergency System
- Manual SOS, Voice SOS, Journey Escalation, User Alert
- MockNotifier (default, no API key needed)
- Email notifier (optional, configure via .env)
- Every notification attempt logged

---

## Architecture

```
SafeHer
│
├── Frontend (HTML / CSS / JS)
│       └── 10 pages — dashboard, journey, plans, contacts, privacy, AI, history
│
├── FastAPI Backend
│       ├── Auth (JWT + bcrypt)
│       ├── Safety Plan Engine
│       ├── Journey Engine (lifecycle + timeline)
│       ├── Safety Signal Engine
│       ├── Privacy Engine
│       ├── AI Safety Module (independent)
│       ├── Emergency Engine
│       └── Notification Service (Mock / Email)
│
└── SQLite (dev) / PostgreSQL (production)
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database ORM | SQLAlchemy 2.0 (async) |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose), bcrypt (passlib) |
| AI / ML | scikit-learn, pandas, NumPy, joblib |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Testing | pytest, pytest-asyncio, httpx |
| Database | SQLite (dev), PostgreSQL (prod) |

---

## Database Design

```
User ──────────────── PrivacySetting (1:1)
  │
  ├── SafetyPlan (1:N)
  │       └── SafetyJourney (1:N)
  │               ├── SafetySignal (1:N)  ──→ SafetyAssessment (1:N)
  │               └── EmergencyEvent (1:N)
  │                       ├── NotificationLog (1:N)
  │
  └── EmergencyContact (1:N)
```

Key design decisions:
- `SafetySignal` is separate from `EmergencyEvent` — signals feed AI, not alerts
- `SafetyAssessment` is AI-only — never directly triggers emergency
- `PrivacySetting` is a core entity, not a config field
- `auto_escalate_on_journey_expiry` defaults to `False`

---

## API Reference

### Authentication
```
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

### Safety Plans
```
GET    /api/safety-plans
POST   /api/safety-plans
GET    /api/safety-plans/{id}
PUT    /api/safety-plans/{id}
DELETE /api/safety-plans/{id}
```

### Journeys
```
POST /api/journeys/start
GET  /api/journeys/active
GET  /api/journeys/{id}
POST /api/journeys/{id}/safe
POST /api/journeys/{id}/extend
POST /api/journeys/{id}/cancel
POST /api/journeys/{id}/complete
GET  /api/journeys/{id}/timeline
```

### Safety Signals
```
POST /api/signals
GET  /api/signals/{journey_id}
```

### AI Safety
```
POST /api/ai/analyze
GET  /api/ai/assessment/{journey_id}
```

### Emergency
```
POST /api/emergency/sos
POST /api/emergency/{id}/cancel
GET  /api/emergency/history
GET  /api/emergency/{id}
```

### Privacy
```
GET /api/privacy
PUT /api/privacy
GET /api/privacy/summary
```

### Contacts
```
GET    /api/contacts
POST   /api/contacts
PUT    /api/contacts/{id}
DELETE /api/contacts/{id}
```

---

## Project Structure

```
SafeHer/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── user.py
│   │   ├── privacy.py
│   │   ├── safety_plan.py
│   │   ├── journey.py
│   │   ├── signal.py
│   │   ├── assessment.py
│   │   ├── contact.py
│   │   ├── emergency.py
│   │   └── notification.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── safety_plan.py
│   │   ├── journey.py
│   │   ├── signal.py
│   │   ├── assessment.py
│   │   ├── contact.py
│   │   ├── emergency.py
│   │   └── privacy.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── safety_plan.py
│   │   ├── journey.py
│   │   ├── signal.py
│   │   ├── ai_safety.py
│   │   ├── contact.py
│   │   ├── emergency.py
│   │   └── privacy.py
│   ├── services/
│   │   ├── safety_plan_service.py
│   │   ├── journey_service.py
│   │   ├── signal_service.py
│   │   ├── ai_service.py
│   │   ├── contact_service.py
│   │   ├── emergency_service.py
│   │   ├── notification_service.py
│   │   └── privacy_service.py
│   ├── auth/
│   │   ├── hashing.py
│   │   ├── jwt_handler.py
│   │   └── dependencies.py
│   └── ai_safety/
│       ├── dataset/
│       │   └── demo_safety_dataset.csv
│       ├── features.py
│       ├── trainer.py
│       └── predictor.py
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── journey.html
│   ├── safety-plan.html
│   ├── contacts.html
│   ├── ai-safety.html
│   ├── privacy.html
│   ├── history.html
│   ├── css/safeher.css
│   └── js/api.js
├── tests/
│   ├── test_auth.py
│   ├── test_safety_plan.py
│   ├── test_journey.py
│   ├── test_signal.py
│   ├── test_privacy.py
│   ├── test_ai.py
│   ├── test_contacts.py
│   └── test_emergency.py
├── data/
├── .env
├── .env.example
├── .gitignore
├── pytest.ini
└── requirements.txt
```

---

## Installation & Setup (Windows)

```powershell
# 1. Clone or download the project
cd SafeHer

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
.\venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy environment file
copy .env.example .env

# 6. Train the AI model (run once)
python -m backend.ai_safety.trainer

# 7. Start the server
python -m uvicorn backend.main:app --reload
```

Open browser: `http://localhost:8000`

---

## Running Tests

```powershell
.\venv\Scripts\activate
pytest tests/ -v
```

Run a specific test file:
```powershell
pytest tests/test_auth.py -v
pytest tests/test_journey.py -v
pytest tests/test_ai.py -v
```

---

## Security

- Passwords hashed with bcrypt (never stored in plain text)
- JWT authentication on all protected endpoints
- User data isolation enforced at service layer (403 on cross-user access)
- No credentials hard-coded — all via `.env`
- Input validation via Pydantic v2
- CORS configured via environment variable
- Internal errors never exposed to client

---

## Privacy Design

- All sensitive features (location, microphone, sharing) **off by default**
- Minimum necessary data collection
- User controls what is included in emergency alerts
- Configurable data retention (0 = do not retain)
- No continuous background tracking
- `auto_escalate_on_journey_expiry` requires explicit opt-in

---

## AI Limitations

- The AI model is trained on **synthetic/demo data** (`demo_safety_dataset.csv`)
- It does **not** use real crime data or real safety incident data
- The model produces **assistive indications only** — not danger verdicts
- The score (0–100) is a software signal, not a measurement of actual risk
- AI failure is handled gracefully — core features continue normally
- The model should not be used to make real-world safety decisions without human judgment

---

## Future Scope

- Real-time journey tracking with WebSocket
- Integration with government emergency APIs (112)
- Community safety heatmaps (anonymized, opt-in)
- Wearable device integration
- Offline SOS capability
- Multi-language support
- PostgreSQL production deployment
- Real SMS integration (Twilio / AWS SNS)

---

## Disclaimer

SafeHer is a B.Tech Computer Science demonstration project. It is an assistive tool only. It does not guarantee safety, predict crime, or replace professional emergency services. The AI model uses synthetic data and its indications should not be treated as factual safety assessments.

---

*Built with Python, FastAPI, SQLAlchemy, scikit-learn — B.Tech CS Final Year Project*
