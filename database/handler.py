import mysql.connector
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from decimal import Decimal
import pandas as pd

from .connection import DatabaseConnection  # Azure MySQL 연결
from .models import StockInfo, DailyCandle, TurtleSignal

# DB 핸들러(쿼리 등) 관리 파일

class DatabaseHandler:
    def __init__(self):
        self.db_conn = DatabaseConnection()  # Azure MySQL 연결 사용
        self.logger = logging.getLogger(__name__)
    
    def create_tables(self):
        """테이블 생성"""
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()
        
        tables = {
            'stock_info': """
                CREATE TABLE IF NOT EXISTS stock_info (
                    stock_code VARCHAR(10) PRIMARY KEY,
                    stock_name VARCHAR(100) NOT NULL,
                    market_type VARCHAR(20),
                    sector VARCHAR(50),
                    market_cap BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            
            'daily_candle': """
                CREATE TABLE IF NOT EXISTS daily_candle (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_code VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    open_price DECIMAL(12,2) NOT NULL,
                    high_price DECIMAL(12,2) NOT NULL,
                    low_price DECIMAL(12,2) NOT NULL,
                    close_price DECIMAL(12,2) NOT NULL,
                    volume BIGINT NOT NULL,
                    amount BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_stock_date (stock_code, date),
                    INDEX idx_stock_code (stock_code),
                    INDEX idx_date (date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            
            'turtle_signals': """
                CREATE TABLE IF NOT EXISTS turtle_signals (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_code VARCHAR(10) NOT NULL,
                    signal_date DATE NOT NULL,
                    system_type TINYINT NOT NULL COMMENT '1:시스템1(단기), 2:시스템2(장기)',
                    signal_type VARCHAR(10) NOT NULL COMMENT 'BUY, SELL',
                    entry_price DECIMAL(12,2) NOT NULL,
                    stop_loss DECIMAL(12,2) NOT NULL,
                    take_profit DECIMAL(12,2) NOT NULL,
                    add_position DECIMAL(12,2) NOT NULL,
                    atr_20 DECIMAL(12,4) NOT NULL,
                    donchian_high_20 DECIMAL(12,2) NOT NULL,
                    donchian_low_20 DECIMAL(12,2) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_stock_code (stock_code),
                    INDEX idx_signal_date (signal_date),
                    INDEX idx_system_type (system_type),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            
            'turtle_positions': """
                CREATE TABLE IF NOT EXISTS turtle_positions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_code VARCHAR(10) NOT NULL,
                    signal_id INT NOT NULL,
                    entry_date DATE NOT NULL,
                    entry_price DECIMAL(12,2) NOT NULL,
                    entry_atr DECIMAL(12,4) NOT NULL COMMENT '진입시 ATR (고정)',
                    fixed_stop_loss DECIMAL(12,2) NOT NULL COMMENT '진입시 계산된 고정 손절가',
                    system_type TINYINT NOT NULL COMMENT '1:시스템1, 2:시스템2',
                    quantity INT DEFAULT 0,
                    current_trailing_stop DECIMAL(12,2) NULL COMMENT '현재 트레일링 스탑',
                    current_add_position DECIMAL(12,2) NULL COMMENT '현재 추가매수가',
                    is_closed BOOLEAN DEFAULT FALSE,
                    exit_date DATE NULL,
                    exit_price DECIMAL(12,2) NULL,
                    exit_reason VARCHAR(20) NULL COMMENT 'STOP_LOSS, TRAILING, MANUAL',
                    profit_loss DECIMAL(15,2) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (signal_id) REFERENCES turtle_signals(id),
                    INDEX idx_stock_code (stock_code),
                    INDEX idx_entry_date (entry_date),
                    INDEX idx_is_closed (is_closed),
                    INDEX idx_system_type (system_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        }
        
        try:
            for table_name, create_sql in tables.items():
                cursor.execute(create_sql)
                self.logger.info(f"{table_name} 테이블 생성/확인 완료")
            
            conn.commit()
            self.logger.info("모든 테이블 생성 완료")
            
        except Exception as e:
            self.logger.error(f"테이블 생성 실패: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    
    def upsert_candle_data(self, candle_data: List[Dict]):
        """일봉 데이터 업서트"""
        if not candle_data:
            return
            
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()
        
        upsert_query = """
            INSERT INTO daily_candle 
            (stock_code, date, open_price, high_price, low_price, close_price, volume, amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                close_price = VALUES(close_price),
                volume = VALUES(volume),
                amount = VALUES(amount)
        """
        
        try:
            data_tuples = [
                (
                    data['stock_code'],
                    data['date'],
                    data['open'],
                    data['high'],
                    data['low'],
                    data['close'],
                    data['volume'],
                    data['amount']
                ) for data in candle_data
            ]
            
            cursor.executemany(upsert_query, data_tuples)
            conn.commit()
            self.logger.info(f"{len(candle_data)}개 일봉 데이터 업서트 완료")
            
        except Exception as e:
            self.logger.error(f"일봉 데이터 업서트 실패: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_candle_data_for_turtle(self, stock_code: str, days: int = 60) -> pd.DataFrame:
        """터틀 계산용 캔들 데이터 조회"""
        conn = self.db_conn.get_connection()
        
        query = """
            SELECT date, open_price, high_price, low_price, close_price, volume
            FROM daily_candle 
            WHERE stock_code = %s 
            ORDER BY date DESC 
            LIMIT %s
        """
        
        try:
            df = pd.read_sql(query, conn, params=(stock_code, days))
            df = df.sort_values('date').reset_index(drop=True)  # 날짜 오름차순 정렬
            return df
            
        except Exception as e:
            self.logger.error(f"{stock_code} 캔들 데이터 조회 실패: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def get_all_active_stocks(self) -> List[str]:
        """활성 종목 코드 리스트 조회"""
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT DISTINCT stock_code 
            FROM daily_candle 
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            ORDER BY stock_code
        """
        
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            return [row[0] for row in results]
            
        except Exception as e:
            self.logger.error(f"활성 종목 조회 실패: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def save_turtle_signals(self, signals: List[TurtleSignal]):
        """터틀 신호 저장"""
        if not signals:
            return
            
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()
        
        insert_query = """
            INSERT INTO turtle_signals 
            (stock_code, signal_date, system_type, signal_type, entry_price, 
             stop_loss, take_profit, add_position, atr_20, donchian_high_20, donchian_low_20)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            data_tuples = [
                (
                    signal.stock_code,
                    signal.signal_date,
                    signal.system_type,
                    signal.signal_type,
                    signal.entry_price,
                    signal.stop_loss,
                    signal.take_profit,
                    signal.add_position,
                    signal.atr_20,
                    signal.donchian_high_20,
                    signal.donchian_low_20
                ) for signal in signals
            ]
            
            cursor.executemany(insert_query, data_tuples)
            conn.commit()
            self.logger.info(f"{len(signals)}개 터틀 신호 저장 완료")
            
        except Exception as e:
            self.logger.error(f"터틀 신호 저장 실패: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
