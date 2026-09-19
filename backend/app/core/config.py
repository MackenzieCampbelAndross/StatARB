from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/statarb_n50"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Market Data
    market_data_api_key: str = ""
    market_data_provider: str = "yahoo_finance"  # Use Yahoo Finance for real-time data
    market_data_cache_ttl: int = 3600

    # Real-time Data
    realtime_data_provider: str = "websocket"
    realtime_reconnect_interval: int = 5
    realtime_heartbeat_interval: int = 30

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    api_workers: int = 4

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # Quantitative Engine Defaults
    default_correlation_threshold: float = 0.70
    default_coint_p_value: float = 0.05
    default_entry_z_score: float = 2.0
    default_exit_z_score: float = 0.0
    default_stop_z_score: float = 4.0
    default_holding_period: int = 30
    default_transaction_cost: float = 0.10
    default_slippage: float = 0.05

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Environment
    environment: str = "development"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
