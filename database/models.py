from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

@dataclass
class StockInfo:
    """종목 정보"""
    stock_code: str
    stock_name: str
    market_type: Optional[str] = None
    sector: Optional[str] = None
    market_cap: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DailyCandle:
    """일봉 데이터"""
    stock_code: str
    date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    amount: int
    created_at: Optional[datetime] = None

@dataclass
class TurtleSignal:
    """터틀 신호 (조건검색 결과)"""
    stock_code: str
    signal_date: date
    system_type: int  # 1: System 1 (단기), 2: System 2 (장기)
    signal_type: str  # 'BUY', 'SELL'
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    add_position: Decimal
    atr_20: Decimal
    donchian_high_20: Decimal
    donchian_low_20: Decimal
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class TurtlePosition:
    """터틀 포지션 (실제 진입한 포지션)"""
    stock_code: str
    signal_id: int
    entry_date: date
    entry_price: Decimal
    entry_atr: Decimal  # 진입시 ATR (고정)
    fixed_stop_loss: Decimal  # 진입시 계산된 고정 손절가
    system_type: int  # 1 또는 2
    quantity: Optional[int] = 0
    current_trailing_stop: Optional[Decimal] = None  # 현재 트레일링 스탑
    current_add_position: Optional[Decimal] = None   # 현재 추가매수가
    is_closed: bool = False
    exit_date: Optional[date] = None
    exit_price: Optional[Decimal] = None
    exit_reason: Optional[str] = None  # 'STOP_LOSS', 'TRAILING', 'MANUAL'
    profit_loss: Optional[Decimal] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None 