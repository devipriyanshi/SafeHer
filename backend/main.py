from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from backend.config import settings
from backend.database import init_db
from backend.routers import auth as auth_router
from backend.routers import safety_plan as safety_plan_router
from backend.routers import journey as journey_router
from backend.routers import signal as signal_router
from backend.routers import privacy as privacy_router
from backend.routers import ai_safety as ai_router
from backend.routers import contact as contact_router
from backend.routers import emergency as emergency_router

# Import all models so SQLAlchemy registers them before create_all
import backend.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Proactive, Privacy-Aware Women Safety & Emergency Assistance Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

app.include_router(auth_router.router)
app.include_router(safety_plan_router.router)
app.include_router(journey_router.router)
app.include_router(signal_router.router)
app.include_router(privacy_router.router)
app.include_router(ai_router.router)
app.include_router(contact_router.router)
app.include_router(emergency_router.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
