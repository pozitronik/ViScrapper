from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import os
from datetime import datetime, timezone
from typing import Dict

from database.session import get_db
from api.models.responses import SuccessResponse, HealthStatus
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Health"])

# Store application start time for uptime calculation
_start_time = None


def get_start_time() -> float:
    """Get the application start time, initializing it if needed."""
    global _start_time
    if _start_time is None:
        _start_time = time.time()
    return _start_time


@router.get("/health", response_model=SuccessResponse[HealthStatus])
async def health_check(db: Session = Depends(get_db)) -> SuccessResponse[HealthStatus]:
    """
    Comprehensive health check endpoint.
    
    Returns system status, database connectivity, uptime, and version information.
    """
    logger.debug("Performing health check")

    # Calculate uptime
    uptime = time.time() - get_start_time()

    # Check database connectivity
    database_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_status = f"error: {str(e)}"

    # Get API version (you might want to store this in a config file)
    api_version = "1.0.0"

    # Determine overall status
    status = "healthy" if database_status == "connected" else "unhealthy"

    health_data = HealthStatus(
        status=status,
        version=api_version,
        uptime=round(uptime, 2),
        database=database_status
    )

    logger.debug(f"Health check completed - status: {status}")

    return SuccessResponse(
        data=health_data,
        message="Health check completed"
    )


@router.get("/status", response_model=SuccessResponse[dict])
async def system_status(db: Session = Depends(get_db)) -> SuccessResponse[dict]:
    """
    Detailed system status endpoint with additional metrics.
    """
    logger.debug("Fetching system status")

    # Calculate uptime
    uptime = time.time() - get_start_time()

    # Check database connectivity with more details
    database_info = {"status": "connected", "details": {}}
    try:
        # Test database with a simple query
        result = db.execute(text("SELECT 1 as test")).first()
        database_info["details"]["test_query"] = "passed" if result and result.test == 1 else "failed"

        # Get SQLite version if using SQLite
        try:
            version_result = db.execute(text("SELECT sqlite_version() as version")).first()
            if version_result:
                database_info["details"]["sqlite_version"] = version_result.version
        except:
            pass  # Not SQLite or version query failed

    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        database_info["status"] = "error"
        database_info["error"] = str(e)

    # System information
    system_info = {
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "platform": os.name,
        "pid": os.getpid(),
        "working_directory": os.getcwd()
    }

    # Environment information (be careful not to expose sensitive data)
    env_info = {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "false").lower() == "true"
    }

    status_data = {
        "overall_status": "healthy" if database_info["status"] == "connected" else "unhealthy",
        "uptime_seconds": round(uptime, 2),
        "uptime_formatted": format_uptime(uptime),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": database_info,
        "system": system_info,
        "environment": env_info
    }

    logger.debug("System status check completed")

    return SuccessResponse(
        data=status_data,
        message="System status retrieved successfully"
    )


def format_uptime(uptime_seconds: float) -> str:
    """Format uptime in a human-readable format."""
    days = int(uptime_seconds // (24 * 3600))
    hours = int((uptime_seconds % (24 * 3600)) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:  # Always show seconds if nothing else
        parts.append(f"{seconds}s")

    return " ".join(parts)


@router.get("/ping")
async def ping() -> Dict[str, str]:
    """Simple ping endpoint for basic connectivity testing."""
    return {"message": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}
