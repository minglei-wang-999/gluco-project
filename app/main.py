import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from contextlib import asynccontextmanager
from .database.database import init_db
from .routers import jobs, meals, users, weixin_auth, auth, subscription
# Import all models to ensure they are registered with SQLAlchemy
import app.models


# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,  # Changed to DEBUG level
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s - %(pathname)s:%(lineno)d",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database connection
    init_db()
    yield
    logger.info("Shutting down server...")


app = FastAPI(
    title="Gluco Backend",
    description="Gluco Backend",
    version="0.1.0",
    lifespan=lifespan,
)  # Enable debug mode

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://0.0.0.0",
        "https://*.ngrok.io",  # ngrok URLs
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(users.router)
app.include_router(weixin_auth.router)
app.include_router(jobs.router)
app.include_router(meals.router)
app.include_router(auth.router)
app.include_router(subscription.router)


@app.get("/health")
async def health_check():
    logger.info("Health check request received")
    return {
        "status": "healthy",
        "debug_mode": app.debug,
        "logging_level": logging.getLogger().level,
    }


if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
