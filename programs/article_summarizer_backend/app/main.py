"""
FastAPI Main Application

Railway-hosted backend for article summarization.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import routes
from app.routes import article, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    # Startup
    logger.info("🚀 Starting Article Summarizer Backend")
    logger.info(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"   Playwright Headless: {os.getenv('PLAYWRIGHT_HEADLESS', 'true')}")

    # Check critical environment variables
    required_vars = ['ANTHROPIC_API_KEY', 'SUPABASE_URL', 'SUPABASE_ANON_KEY', 'API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
    else:
        logger.info("✅ All required environment variables present")

    # Check storage directory
    storage_dir = os.getenv('STORAGE_DIR', '/app/storage')
    if os.path.exists(storage_dir):
        logger.info(f"✅ Storage directory exists: {storage_dir}")

        # Check for storage_state.json
        storage_state_file = os.path.join(storage_dir, 'storage_state.json')
        if os.path.exists(storage_state_file):
            logger.info(f"✅ Browser session state found: {storage_state_file}")
        else:
            logger.warning(f"⚠️ No browser session state found. Run setup_auth.py to configure authentication.")
    else:
        logger.warning(f"⚠️ Storage directory not found: {storage_dir}")

    yield

    # Shutdown
    logger.info("👋 Shutting down Article Summarizer Backend")


# Create FastAPI app
app = FastAPI(
    title="Article Summarizer API",
    description="Backend service for processing and summarizing articles",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(article.router, prefix="/api", tags=["articles"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Article Summarizer API",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check if Playwright is available
    playwright_available = False
    try:
        from playwright.sync_api import sync_playwright
        playwright_available = True
    except ImportError:
        pass

    # Check storage
    storage_dir = os.getenv('STORAGE_DIR', '/app/storage')
    storage_exists = os.path.exists(storage_dir)

    # Check browser session
    storage_state_file = os.path.join(storage_dir, 'storage_state.json')
    session_configured = os.path.exists(storage_state_file)

    return {
        "status": "healthy",
        "playwright": playwright_available,
        "storage": storage_exists,
        "session_configured": session_configured,
        "environment": os.getenv('ENVIRONMENT', 'development')
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )
