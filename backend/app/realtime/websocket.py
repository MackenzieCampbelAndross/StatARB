from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Optional
import json
import asyncio
from datetime import datetime
import logging

from app.database.session import get_db
from app.models.pair import Pair as PairModel
from app.models.price import Price
from app.quant.signals.engine import SignalEngine
from app.quant.spread.calculator import SpreadCalculator
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Initialize quantitative engines
signal_engine = SignalEngine()
spread_calculator = SpreadCalculator()


class ConnectionManager:
    """Manages WebSocket connections for real-time signal streaming."""

    def __init__(self):
        # Dictionary to store active connections: {websocket: client_id}
        self.active_connections: Dict[WebSocket, str] = {}
        # Dictionary to store client subscriptions: {client_id: {pair_ids}}
        self.subscriptions: Dict[str, Set[str]] = {}
        # Dictionary to store client last heartbeat: {client_id: timestamp}
        self.client_heartbeats: Dict[str, datetime] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[websocket] = client_id
        self.subscriptions[client_id] = set()
        self.client_heartbeats[client_id] = datetime.now()
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection."""
        client_id = self.active_connections.pop(websocket, None)
        if client_id:
            self.subscriptions.pop(client_id, None)
            self.client_heartbeats.pop(client_id, None)
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")

    def subscribe(self, client_id: str, pair_ids: Set[str]):
        """Subscribe a client to specific pairs."""
        if client_id in self.subscriptions:
            self.subscriptions[client_id].update(pair_ids)
            logger.info(f"Client {client_id} subscribed to {len(pair_ids)} pairs")

    def unsubscribe(self, client_id: str, pair_ids: Set[str]):
        """Unsubscribe a client from specific pairs."""
        if client_id in self.subscriptions:
            self.subscriptions[client_id].difference_update(pair_ids)
            logger.info(f"Client {client_id} unsubscribed from {len(pair_ids)} pairs")

    def update_heartbeat(self, client_id: str):
        """Update client heartbeat timestamp."""
        self.client_heartbeats[client_id] = datetime.now()

    def get_subscribers(self, pair_id: str) -> Set[WebSocket]:
        """Get all websockets subscribed to a specific pair."""
        subscribers = set()
        for websocket, client_id in self.active_connections.items():
            if client_id in self.subscriptions and pair_id in self.subscriptions[client_id]:
                subscribers.add(websocket)
        return subscribers

    async def broadcast_to_subscribers(self, pair_id: str, message: dict):
        """Broadcast a message to all subscribers of a specific pair."""
        subscribers = self.get_subscribers(pair_id)
        if subscribers:
            for websocket in subscribers:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to subscriber: {e}")
                    # Remove broken connection
                    self.disconnect(websocket)

    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected clients."""
        for websocket in list(self.active_connections.keys()):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                self.disconnect(websocket)

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)

    def get_client_info(self) -> Dict:
        """Get information about connected clients."""
        return {
            'total_connections': len(self.active_connections),
            'clients': [
                {
                    'client_id': client_id,
                    'subscriptions': list(subs),
                    'last_heartbeat': heartbeat.isoformat()
                }
                for client_id, subs in self.subscriptions.items()
                for heartbeat in [self.client_heartbeats.get(client_id)]
            ]
        }


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time signal streaming.

    Client can send messages to:
    - Subscribe to pairs: {"action": "subscribe", "pair_ids": ["pair1", "pair2"]}
    - Unsubscribe from pairs: {"action": "unsubscribe", "pair_ids": ["pair1"]}
    - Heartbeat: {"action": "heartbeat"}

    Server sends:
    - Signal updates: {"type": "signal", "pair": "...", "priceA": ..., "priceB": ..., "spread": ..., "zScore": ..., "signal": "...", "timestamp": "..."}
    - Connection status: {"type": "status", "status": "connected"/"disconnected", "message": "..."}
    - Error messages: {"type": "error", "message": "..."}
    """
    client_id = f"client_{id(websocket)}"
    await manager.connect(websocket, client_id)

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "status",
            "status": "connected",
            "message": "WebSocket connection established",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        })

        # Start background task to send periodic updates
        update_task = asyncio.create_task(send_periodic_updates(websocket, client_id, db))

        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)

                if message.get("action") == "subscribe":
                    pair_ids = set(message.get("pair_ids", []))
                    manager.subscribe(client_id, pair_ids)
                    await websocket.send_json({
                        "type": "status",
                        "status": "subscribed",
                        "pair_ids": list(pair_ids),
                        "timestamp": datetime.now().isoformat()
                    })

                elif message.get("action") == "unsubscribe":
                    pair_ids = set(message.get("pair_ids", []))
                    manager.unsubscribe(client_id, pair_ids)
                    await websocket.send_json({
                        "type": "status",
                        "status": "unsubscribed",
                        "pair_ids": list(pair_ids),
                        "timestamp": datetime.now().isoformat()
                    })

                elif message.get("action") == "heartbeat":
                    manager.update_heartbeat(client_id)
                    await websocket.send_json({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.now().isoformat()
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {message.get('action')}"
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        update_task.cancel()
        manager.disconnect(websocket)
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        update_task.cancel()
        manager.disconnect(websocket)
        logger.error(f"WebSocket error for client {client_id}: {e}")


async def send_periodic_updates(websocket: WebSocket, client_id: str, db: Session):
    """
    Send periodic updates to connected clients.

    This is a simplified implementation that sends simulated updates.
    In production, this would:
    1. Connect to real-time market data feed
    2. Process price updates as they arrive
    3. Calculate updated spreads and Z-scores
    4. Generate new signals
    5. Push updates to subscribed clients
    """
    try:
        while True:
            # Check if client is still connected
            if websocket not in manager.active_connections:
                break

            # Get client subscriptions
            subscriptions = manager.subscriptions.get(client_id, set())

            if subscriptions:
                # Send updates for subscribed pairs
                for pair_id in subscriptions:
                    try:
                        # Get current signal data for the pair
                        signal_data = await get_current_signal_data(pair_id, db)

                        if signal_data:
                            await websocket.send_json({
                                "type": "signal",
                                **signal_data
                            })

                    except Exception as e:
                        logger.error(f"Error getting signal data for pair {pair_id}: {e}")

            # Wait before next update (simulated real-time)
            # In production, this would be event-driven based on market data
            await asyncio.sleep(5)  # Send updates every 5 seconds

    except asyncio.CancelledError:
        logger.info(f"Update task cancelled for client {client_id}")
    except Exception as e:
        logger.error(f"Error in periodic updates for client {client_id}: {e}")


async def get_current_signal_data(pair_id: str, db: Session) -> Optional[dict]:
    """
    Get current signal data for a specific pair.

    This matches the frontend SignalStreamEvent type:
    {
      pair: string
      priceA: number
      priceB: number
      spread: number
      zScore: number
      signal: string
      timestamp: string
    }
    """
    try:
        # Get pair from database
        pair = db.query(PairModel).filter(PairModel.id == pair_id).first()
        if not pair:
            return None

        # Get latest prices
        latest_price_a = db.query(Price).filter(
            Price.symbol == pair.symbol_a
        ).order_by(Price.timestamp.desc()).first()

        latest_price_b = db.query(Price).filter(
            Price.symbol == pair.symbol_b
        ).order_by(Price.timestamp.desc()).first()

        if not latest_price_a or not latest_price_b:
            return None

        # Calculate current metrics
        # (This would use real-time calculation in production)
        hedge_ratio = pair.hedge_ratio or 1.0
        spread = latest_price_a.close - hedge_ratio * latest_price_b.close

        # Get Z-score and signal from recent data
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        prices_a = db.query(Price).filter(
            Price.symbol == pair.symbol_a,
            Price.timestamp >= start_date,
            Price.timestamp <= end_date
        ).order_by(Price.timestamp).all()

        prices_b = db.query(Price).filter(
            Price.symbol == pair.symbol_b,
            Price.timestamp >= start_date,
            Price.timestamp <= end_date
        ).order_by(Price.timestamp).all()

        current_z = 0.0
        current_signal = "WATCH"

        if prices_a and prices_b and len(prices_a) >= 20 and len(prices_b) >= 20:
            import pandas as pd
            series_a = pd.Series([p.close for p in prices_a])
            series_b = pd.Series([p.close for p in prices_b])

            spread_series = spread_calculator.calculate_spread(series_a, series_b, hedge_ratio)
            rolling_stats = spread_calculator.calculate_rolling_statistics(spread_series, window=20)
            z_score = spread_calculator.calculate_z_score(
                spread_series,
                rolling_stats['rolling_mean'],
                rolling_stats['rolling_std'],
                window=20
            )

            current_z = z_score.iloc[-1] if len(z_score) > 0 else 0.0

            signal_info = signal_engine.generate_signal(current_z)
            current_signal = signal_info['signal']

        return {
            "pair": f"{pair.symbol_a} / {pair.symbol_b}",
            "priceA": round(latest_price_a.close, 2),
            "priceB": round(latest_price_b.close, 2),
            "spread": round(spread, 2),
            "zScore": round(current_z, 2),
            "signal": current_signal,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting current signal data for pair {pair_id}: {e}")
        return None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return manager


def get_websocket_status() -> dict:
    """Get WebSocket connection status."""
    return {
        "status": "connected" if manager.get_connection_count() > 0 else "not_connected",
        "active_connections": manager.get_connection_count(),
        "client_info": manager.get_client_info()
    }
