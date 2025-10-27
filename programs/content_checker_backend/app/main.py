"""
Content Checker Backend - Main FastAPI Application
Provides API for checking new podcasts and posts
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routes import podcasts, posts

# Load environment variables
load_dotenv('.env.local')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    logger.info("Content Checker Backend starting up...")
    yield
    logger.info("Content Checker Backend shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Content Checker Backend",
    description="API for checking new podcasts and newsletter posts",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:3001').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(podcasts.router, prefix="/api", tags=["podcasts"])
app.include_router(posts.router, prefix="/api", tags=["posts"])


@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns:
        Health status and configuration checks
    """
    # Check if required environment variables are set
    pocketcasts_configured = bool(
        os.getenv('POCKETCASTS_EMAIL') and os.getenv('POCKETCASTS_PASSWORD')
    )
    database_configured = bool(
        os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )
    serpapi_configured = bool(os.getenv('SERPAPI_KEY'))

    # Test database connection
    database_connected = False
    if database_configured:
        try:
            from supabase import create_client
            supabase = create_client(
                os.getenv('SUPABASE_URL'),
                os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            )
            # Try a simple query
            supabase.table('content_queue').select('id').limit(1).execute()
            database_connected = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

    return {
        "status": "healthy",
        "pocketcasts_configured": pocketcasts_configured,
        "database_configured": database_configured,
        "database_connected": database_connected,
        "serpapi_configured": serpapi_configured,
        "cors_origins": cors_origins
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Content Checker Backend API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
