from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal

# 데이터 모델 정의 파일 (Azure MySQL 사용)

@dataclass
class StockInfo:
    stock_code: str
    stock_name: str
    market_type: str
    sector: Optional[str] = None
    market_cap: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass 
class DailyCandle:
    stock_code: str
    date: str
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    amount: int
    created_at: Optional[datetime] = None

@dataclass
class TurtleSignal:
    stock_code: str
    signal_date: str
    system_type: int  # 1: 시스템1(단기), 2: 시스템2(장기)
    signal_type: str  # 'BUY', 'SELL'
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    add_position: Decimal
    atr_20: Decimal  # ATR 값
    donchian_high_20: Decimal  # 돈치안 채널 상단
    donchian_low_20: Decimal   # 돈치안 채널 하단
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
