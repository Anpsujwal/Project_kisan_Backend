from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .routers import chat, disease, market, schemes, utilities, users
from .routers import auth

app = FastAPI(title="Project Kisan Backend", version="0.1.0")

# CORS (development-friendly; tighten later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(disease.router, prefix="/api", tags=["disease"])
app.include_router(market.router, prefix="/api", tags=["market"])
app.include_router(schemes.router, prefix="/api", tags=["schemes"])
app.include_router(utilities.router, prefix="/api", tags=["utilities"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(auth.router, prefix="/api", tags=["auth"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Load .env on startup
@app.on_event("startup")
async def load_env():
    load_dotenv()
