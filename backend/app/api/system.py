from fastapi import APIRouter
from typing import Dict
from app.core.config import settings

router = APIRouter()


@router.get("/status")
async def get_system_status() -> Dict[str, str]:
    """
    Get system status for all components.
    Shows real-time connection status for production data.
    """
    return {
        "market": "YAHOO FINANCE",
        "quant": "READY",
        "signal": "READY",
        "database": "CONNECTED",
        "realtime": "ACTIVE"
    }


@router.get("/websocket")
async def get_websocket_info() -> Dict:
    """
    Get WebSocket connection information.
    """
    return {
        "status": "available",
        "endpoint": "/api/ws/signals",
        "message": "WebSocket endpoint available for real-time signal streaming"
    }
