"""Simple script to run the FastAPI server."""
import os
import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=os.getenv("UVICORN_RELOAD", "1") == "1"
    )

