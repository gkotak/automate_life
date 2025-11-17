"""
FastAPI Main Application

Railway-hosted backend for article summarization.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv('.env.local')

# Setup logging with rotation
logs_dir = Path(__file__).parent.parent / 'logs'
logs_dir.mkdir(parents=True, exist_ok=True)
log_file = logs_dir / 'backend.log'

# Create handlers
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10_000_000,  # 10MB per file
    backupCount=5,  # Keep 5 backup files
    encoding='utf-8'
)
console_handler = logging.StreamHandler()

# Set format
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Configure root logger with environment variable support
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file}")

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
    required_vars = ['ANTHROPIC_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'API_KEY']
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

    # Check browser session (Supabase or file)
    session_configured = False
    session_source = None

    # First check Supabase
    try:
        from supabase import create_client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if supabase_url and supabase_key:
            supabase = create_client(supabase_url, supabase_key)
            result = supabase.table('browser_sessions')\
                .select('id')\
                .eq('platform', 'all')\
                .eq('is_active', True)\
                .limit(1)\
                .execute()

            if result.data and len(result.data) > 0:
                session_configured = True
                session_source = "supabase"
    except Exception:
        pass

    # Fallback to file-based session
    if not session_configured:
        storage_state_file = os.path.join(storage_dir, 'storage_state.json')
        if os.path.exists(storage_state_file):
            session_configured = True
            session_source = "file"

    return {
        "status": "healthy",
        "playwright": playwright_available,
        "storage": storage_exists,
        "session_configured": session_configured,
        "session_source": session_source,
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
