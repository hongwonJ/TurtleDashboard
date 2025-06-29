import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from decimal import Decimal
from datetime import datetime
import logging

from database.models import TurtleSignal

class TurtleCalculator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """ATR (Average True Range) 계산"""
        high = df['high_price']
        low = df['low_price']
        close = df['close_price'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def calculate_donchian_channel(self, df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series]:
        """돈치안 채널 계산"""
        high_channel = df['high_price'].rolling(window=period).max()
        low_channel = df['low_price'].rolling(window=period).min()
        
        return high_channel, low_channel
    
    def calculate_turtle_system1(self, df: pd.DataFrame, current_date: str) -> Optional[TurtleSignal]:
        """터틀 시스템 1 (단기) 신호 계산"""
        if len(df) < 30:  # 최소 30일 데이터 필요
            return None
        
        # 20일 돈치안 채널과 ATR 계산
        atr = self.calculate_atr(df, 20)
        high_channel, low_channel = self.calculate_donchian_channel(df, 20)
        
        # 10일 돈치안 채널 (exit용)
        exit_high, exit_low = self.calculate_donchian_channel(df, 10)
        
        current_price = df['close_price'].iloc[-1]
        prev_high_channel = high_channel.iloc[-2]  # 전일 채널
        prev_low_channel = low_channel.iloc[-2]
        current_atr = atr.iloc[-1]
        
        if pd.isna(current_atr) or pd.isna(prev_high_channel):
            return None
        
        signal = None
        
        # 매수 신호: 현재가가 20일 최고가를 돌파
        if current_price > prev_high_channel:
            entry_price = current_price
            stop_loss = entry_price - (2 * current_atr)  # 2ATR 손절
            take_profit = entry_price + (4 * current_atr)  # 4ATR 익절
            add_position = entry_price + (0.5 * current_atr)  # 0.5ATR 추가매수
            
            signal = TurtleSignal(
                stock_code=df.iloc[-1].get('stock_code', ''),
                signal_date=current_date,
                system_type=1,
                signal_type='BUY',
                entry_price=Decimal(str(round(entry_price, 2))),
                stop_loss=Decimal(str(round(stop_loss, 2))),
                take_profit=Decimal(str(round(take_profit, 2))),
                add_position=Decimal(str(round(add_position, 2))),
                atr_20=Decimal(str(round(current_atr, 4))),
                donchian_high_20=Decimal(str(round(prev_high_channel, 2))),
                donchian_low_20=Decimal(str(round(prev_low_channel, 2)))
            )
        
        # 매도 신호: 현재가가 20일 최저가를 하향 돌파
        elif current_price < prev_low_channel:
            entry_price = current_price
            stop_loss = entry_price + (2 * current_atr)  # 2ATR 손절
            take_profit = entry_price - (4 * current_atr)  # 4ATR 익절
            add_position = entry_price - (0.5 * current_atr)  # 0.5ATR 추가매수
            
            signal = TurtleSignal(
                stock_code=df.iloc[-1].get('stock_code', ''),
                signal_date=current_date,
                system_type=1,
                signal_type='SELL',
                entry_price=Decimal(str(round(entry_price, 2))),
                stop_loss=Decimal(str(round(stop_loss, 2))),
                take_profit=Decimal(str(round(take_profit, 2))),
                add_position=Decimal(str(round(add_position, 2))),
                atr_20=Decimal(str(round(current_atr, 4))),
                donchian_high_20=Decimal(str(round(prev_high_channel, 2))),
                donchian_low_20=Decimal(str(round(prev_low_channel, 2)))
            )
        
        return signal
    
    def calculate_turtle_system2(self, df: pd.DataFrame, current_date: str) -> Optional[TurtleSignal]:
        """터틀 시스템 2 (장기) 신호 계산"""
        if len(df) < 60:  # 최소 60일 데이터 필요
            return None
        
        # 55일 돈치안 채널과 ATR 계산
        atr = self.calculate_atr(df, 20)
        high_channel, low_channel = self.calculate_donchian_channel(df, 55)
        
        # 20일 돈치안 채널 (exit용)
        exit_high, exit_low = self.calculate_donchian_channel(df, 20)
        
        current_price = df['close_price'].iloc[-1]
        prev_high_channel = high_channel.iloc[-2]
        prev_low_channel = low_channel.iloc[-2]
        current_atr = atr.iloc[-1]
        
        if pd.isna(current_atr) or pd.isna(prev_high_channel):
            return None
        
        signal = None
        
        # 매수 신호: 현재가가 55일 최고가를 돌파
        if current_price > prev_high_channel:
            entry_price = current_price
            stop_loss = entry_price - (2 * current_atr)
            take_profit = entry_price + (6 * current_atr)  # 시스템2는 더 큰 수익 목표
            add_position = entry_price + (0.5 * current_atr)
            
            signal = TurtleSignal(
                stock_code=df.iloc[-1].get('stock_code', ''),
                signal_date=current_date,
                system_type=2,
                signal_type='BUY',
                entry_price=Decimal(str(round(entry_price, 2))),
                stop_loss=Decimal(str(round(stop_loss, 2))),
                take_profit=Decimal(str(round(take_profit, 2))),
                add_position=Decimal(str(round(add_position, 2))),
                atr_20=Decimal(str(round(current_atr, 4))),
                donchian_high_20=Decimal(str(round(prev_high_channel, 2))),
                donchian_low_20=Decimal(str(round(prev_low_channel, 2)))
            )
        
        elif current_price < prev_low_channel:
            entry_price = current_price
            stop_loss = entry_price + (2 * current_atr)
            take_profit = entry_price - (6 * current_atr)
            add_position = entry_price - (0.5 * current_atr)
            
            signal = TurtleSignal(
                stock_code=df.iloc[-1].get('stock_code', ''),
                signal_date=current_date,
                system_type=2,
                signal_type='SELL',
                entry_price=Decimal(str(round(entry_price, 2))),
                stop_loss=Decimal(str(round(stop_loss, 2))),
                take_profit=Decimal(str(round(take_profit, 2))),
                add_position=Decimal(str(round(add_position, 2))),
                atr_20=Decimal(str(round(current_atr, 4))),
                donchian_high_20=Decimal(str(round(prev_high_channel, 2))),
                donchian_low_20=Decimal(str(round(prev_low_channel, 2)))
            )
        
        return signal