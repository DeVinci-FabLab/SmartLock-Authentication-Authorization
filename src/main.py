import logging
import sys

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware  # ADD THIS

from src.routes import categories, items, lockers, stock, badge
from src.database.session import engine
from src.database.base import Base 
from src.utils.middleware_logger import LoggingMiddleware
from src.utils.logger import setup_logger, logger

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting application...")
    
    try : 
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        raise
    
    logger.success("✅ Application startup complete.")
    yield
    
    logger.info("🛑 Shutting down application...")
    logger.success("✅ Application shutdown complete.")

app = FastAPI(
    title="Smartlock API",
    description="API for managing smart locks, categories, and items.",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan
)

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ADD SLOWAPI MIDDLEWARE - This is crucial!
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(
    LoggingMiddleware,
    log_request_body=False,
    log_response_body=False,
)


# Redirect uvicorn logs to Loguru
class InterceptHandler(logging.Handler):
    """
    Intercept standard logging and redirect to Loguru
    """
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = "INFO"
        
        # Find caller
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# Setup logging intercept for uvicorn and other libraries
logging.root.handlers = [InterceptHandler()]
logging.root.setLevel(logging.INFO)

for name in logging.root.manager.loggerDict.keys():
    logging.getLogger(name).handlers = []
    logging.getLogger(name).propagate = True

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with logging
    """
    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={
            "errors": exc.errors(),
            "body": exc.body,
        }
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle general exceptions with logging
    """
    logger.exception(
        f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc),
        },
    )


@app.get("/health", tags=["System"])
@limiter.limit("60/minute")  # Changed to 60/minute for reasonable testing
def health_check(request: Request):
    logger.info("Health check endpoint called")
    return {
        "status": "healthy", 
        "service": "Smartlock API",
        "version": "0.1.0"
    }
    
@app.get("/", tags=["System"])
@limiter.limit("100/minute") 
def root(request: Request):  
    logger.info("Root endpoint called")
    return {
        "message": "Welcome to the Smartlock API",
        "docs": "/docs",
        "health": "/health",
        "version": "0.1.0"
    }


app.include_router(categories.router)
app.include_router(items.router)
app.include_router(lockers.router)
app.include_router(stock.router)
app.include_router(badge.router)


if __name__ == "__main__":
    import uvicorn
    
    setup_logger(level="DEBUG", log_to_file=True)  
    
    logger.info("Starting Smartlock API with Uvicorn...")
    
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True, log_config=None)