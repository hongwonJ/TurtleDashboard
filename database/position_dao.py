import logging
from typing import List, Optional, Dict
from datetime import date
from decimal import Decimal

from .connection import DatabaseConnection
from .models import TurtlePosition

class PositionDAO:
    """터틀 포지션 관리 DAO"""
    
    def __init__(self):
        self.db_conn = DatabaseConnection()
        self.logger = logging.getLogger(__name__)
    
    def create_position(self, position: TurtlePosition) -> int:
        """새 포지션 생성"""
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO turtle_positions 
            (stock_code, signal_id, entry_date, entry_price, entry_atr, 
             fixed_stop_loss, system_type, quantity, current_trailing_stop, current_add_position)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            cursor.execute(query, (
                position.stock_code,
                position.signal_id,
                position.entry_date,
                position.entry_price,
                position.entry_atr,
                position.fixed_stop_loss,
                position.system_type,
                position.quantity,
                position.current_trailing_stop,
                position.current_add_position
            ))
            conn.commit()
            position_id = cursor.lastrowid
            self.logger.info(f"포지션 생성: {position.stock_code} (ID: {position_id})")
            return position_id
            
        except Exception as e:
            self.logger.error(f"포지션 생성 실패: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_active_positions(self) -> List[TurtlePosition]:
        """활성 포지션 조회"""
        conn = self.db_conn.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT * FROM turtle_positions 
            WHERE is_closed = FALSE 
            ORDER BY entry_date DESC, stock_code
        """
        
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            positions = []
            for row in rows:
                position = TurtlePosition(
                    id=row['id'],
                    stock_code=row['stock_code'],
                    signal_id=row['signal_id'],
                    entry_date=row['entry_date'],
                    entry_price=row['entry_price'],
                    entry_atr=row['entry_atr'],
                    fixed_stop_loss=row['fixed_stop_loss'],
                    system_type=row['system_type'],
                    quantity=row['quantity'],
                    current_trailing_stop=row['current_trailing_stop'],
                    current_add_position=row['current_add_position'],
                    is_closed=row['is_closed'],
                    exit_date=row['exit_date'],
                    exit_price=row['exit_price'],
                    exit_reason=row['exit_reason'],
                    profit_loss=row['profit_loss'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                positions.append(position)
            
            return positions
            
        except Exception as e:
            self.logger.error(f"활성 포지션 조회 실패: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_position_by_stock(self, stock_code: str) -> Optional[TurtlePosition]:
        """종목별 활성 포지션 조회"""
        conn = self.db_conn.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT * FROM turtle_positions 
            WHERE stock_code = %s AND is_closed = FALSE 
            ORDER BY entry_date DESC 
            LIMIT 1
        """
        
        try:
            cursor.execute(query, (stock_code,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return TurtlePosition(
                id=row['id'],
                stock_code=row['stock_code'],
                signal_id=row['signal_id'],
                entry_date=row['entry_date'],
                entry_price=row['entry_price'],
                entry_atr=row['entry_atr'],
                fixed_stop_loss=row['fixed_stop_loss'],
                system_type=row['system_type'],
                quantity=row['quantity'],
                current_trailing_stop=row['current_trailing_stop'],
                current_add_position=row['current_add_position'],
                is_closed=row['is_closed'],
                exit_date=row['exit_date'],
                exit_price=row['exit_price'],
                exit_reason=row['exit_reason'],
                profit_loss=row['profit_loss'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
        except Exception as e:
            self.logger.error(f"종목별 포지션 조회 실패 ({stock_code}): {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def update_trailing_stop(self, position_id: int, trailing_stop: Decimal, add_position: Decimal) -> bool:
        """트레일링 스탑 및 추가매수가 업데이트"""
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()
        
        query = """
            UPDATE turtle_positions 
            SET current_trailing_stop = %s, current_add_position = %s
            WHERE id = %s AND is_closed = FALSE
        """
        
        try:
            cursor.execute(query, (trailing_stop, add_position, position_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                self.logger.info(f"트레일링 스탑 업데이트: ID {position_id}, 트레일링: {trailing_stop}")
                return True
            else:
                self.logger.warning(f"트레일링 스탑 업데이트 실패: 포지션 ID {position_id} 없음")
                return False
                
        except Exception as e:
            self.logger.error(f"트레일링 스탑 업데이트 실패: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def close_position(self, position_id: int, exit_date: date, exit_price: Decimal, 
                      exit_reason: str, profit_loss: Decimal) -> bool:
        """포지션 종료"""
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()
        
        query = """
            UPDATE turtle_positions 
            SET is_closed = TRUE, exit_date = %s, exit_price = %s, 
                exit_reason = %s, profit_loss = %s
            WHERE id = %s AND is_closed = FALSE
        """
        
        try:
            cursor.execute(query, (exit_date, exit_price, exit_reason, profit_loss, position_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                self.logger.info(f"포지션 종료: ID {position_id}, 종료사유: {exit_reason}, 손익: {profit_loss}")
                return True
            else:
                self.logger.warning(f"포지션 종료 실패: 포지션 ID {position_id} 없음")
                return False
                
        except Exception as e:
            self.logger.error(f"포지션 종료 실패: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def get_positions_summary(self) -> Dict:
        """포지션 요약 통계"""
        conn = self.db_conn.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 활성 포지션 수
            cursor.execute("SELECT COUNT(*) as active_count FROM turtle_positions WHERE is_closed = FALSE")
            active_count = cursor.fetchone()['active_count']
            
            # 총 포지션 수
            cursor.execute("SELECT COUNT(*) as total_count FROM turtle_positions")
            total_count = cursor.fetchone()['total_count']
            
            # 수익 통계
            cursor.execute("""
                SELECT 
                    COUNT(*) as closed_count,
                    SUM(profit_loss) as total_pnl,
                    AVG(profit_loss) as avg_pnl,
                    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as win_count
                FROM turtle_positions 
                WHERE is_closed = TRUE AND profit_loss IS NOT NULL
            """)
            pnl_stats = cursor.fetchone()
            
            return {
                'active_positions': active_count,
                'total_positions': total_count,
                'closed_positions': pnl_stats['closed_count'] or 0,
                'total_pnl': float(pnl_stats['total_pnl'] or 0),
                'avg_pnl': float(pnl_stats['avg_pnl'] or 0),
                'win_count': pnl_stats['win_count'] or 0,
                'win_rate': (pnl_stats['win_count'] or 0) / max(pnl_stats['closed_count'] or 1, 1) * 100
            }
            
        except Exception as e:
            self.logger.error(f"포지션 요약 조회 실패: {e}")
            return {}
        finally:
            cursor.close()
            conn.close() 