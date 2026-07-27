import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import engine, Base
from app.routers import auth, users, calls, chat, notifications, agora

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Agora Audio/Video Call, Chat & Notification Backend API",
    description="FastAPI REST Backend for Flutter app with Agora RTC Tokens, Chat History, Call History, and Notifications.",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(calls.router)
app.include_router(chat.router)
app.include_router(notifications.router)
app.include_router(agora.router)

# Serve Static Files for Interactive Web Dashboard
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=FileResponse)
    def read_dashboard():
        return os.path.join(static_dir, "index.html")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Agora FastAPI Backend Service is Running"}
