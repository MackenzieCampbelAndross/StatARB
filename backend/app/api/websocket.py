from fastapi import APIRouter, WebSocket
from app.realtime.websocket import websocket_endpoint

router = APIRouter()

# WebSocket endpoint
@router.websocket("/signals")
async def websocket_signals(websocket: WebSocket):
    """
    WebSocket endpoint for real-time signal streaming.
    """
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        await websocket_endpoint(websocket, db)
    finally:
        db.close()
