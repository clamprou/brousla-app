"""FastAPI application entry point."""
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes_auth import router as auth_router
from app.routes_ai import router as ai_router
from app.routes_subscription import router as subscription_router
from app.config import settings

# Configure logging (default INFO; opt-in DEBUG via LOG_LEVEL)
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=_LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
if _LOG_LEVEL == "DEBUG":
    logging.getLogger("app.routes_ai").setLevel(logging.DEBUG)
    logging.getLogger("app.llm.openai_client").setLevel(logging.DEBUG)
    logging.getLogger("app.llm").setLevel(logging.DEBUG)

app = FastAPI(
    title="Brousla App Server",
    description="Backend API server for Brousla desktop app",
    version="1.0.0"
)

# CORS middleware
# - Packaged Electron requests often send Origin: null
# - Do not use allow_credentials=True with wildcard origins
_cors_origins = [
    o.strip()
    for o in (settings.cors_allow_origins or "").split(",")
    if o and o.strip()
]
if not _cors_origins:
    _cors_origins = ["null"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=bool(settings.cors_allow_credentials),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(subscription_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Brousla App Server API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=os.getenv("UVICORN_RELOAD", "0") == "1"
    )

