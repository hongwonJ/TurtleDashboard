import schedule
import time
import asyncio
import threading
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
from decimal import Decimal
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
from services.kiwoom_service import KiwoomAPIService
from services.turtle_calculator import TurtleCalculator
from database.position_dao import PositionDAO
from database.handler import DatabaseHandler
from database.models import TurtlePosition
from config import Config

logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = ZoneInfo("Asia/Seoul")

class DailyScheduler:
    def __init__(self):
        self.kiwoom_service = KiwoomAPIService()
        self.turtle_calculator = TurtleCalculator()
        self.logger = logging.getLogger(__name__)
        self.kst = KST  # KST 시간대 참조
        
        # DB 연결 시도 (실패해도 계속 진행)
        self.db_available = False
        try:
            self.position_dao = PositionDAO()
            self.db_handler = DatabaseHandler()
            self.db_available = True
            self.logger.info("✅ 데이터베이스 연결 성공")
        except Exception as e:
            self.logger.warning(f"⚠️ 데이터베이스 연결 실패 (키움 API만 사용): {e}")
            self.position_dao = None
            self.db_handler = None
        
        # 조건검색 seq 번호들을 동적으로 찾기
        self.condition_sequences = []
        self.system_seq_mapping = {}  # seq -> system name 매핑
        self._initialize_system_sequences()

    def get_kst_now(self):
        """KST 기준 현재 시간 반환"""
        return datetime.now(self.kst)

    def _initialize_system_sequences(self):
        """조건식 목록에서 System 1, System 2에 해당하는 seq을 찾아 초기화"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            condition_list = loop.run_until_complete(self.kiwoom_service.get_condition_list())
            loop.close()
            
            for condition in condition_list:
                seq = str(condition.get('seq', ''))
                name = condition.get('name', '').strip()
                
                if 'system 1' in name.lower():
                    self.condition_sequences.append(seq)
                    self.system_seq_mapping[seq] = '1'
                    self.logger.info(f"System 1 조건식 발견: seq={seq}, name={name}")
                elif 'system 2' in name.lower():
                    self.condition_sequences.append(seq)
                    self.system_seq_mapping[seq] = '2'
                    self.logger.info(f"System 2 조건식 발견: seq={seq}, name={name}")
            
            if not self.condition_sequences:
                self.logger.warning("System 1, System 2 조건식을 찾을 수 없습니다.")
            else:
                self.logger.info(f"초기화 완료: {len(self.condition_sequences)}개 조건식 발견")
                
        except Exception as e:
            self.logger.error(f"조건식 seq 초기화 실패: {e}")
            self.condition_sequences = []
            self.system_seq_mapping = {}

    async def _enhance_with_turtle_data(self, stocks: List[Dict[str, str]], system_type: int) -> List[Dict[str, str]]:
        """조건검색 결과에 터틀 계산 데이터 추가"""
        enhanced_stocks = []
        
        for stock in stocks:
            try:
                stock_code = stock.get('code', '')
                if not stock_code:
                    enhanced_stocks.append(stock)
                    continue
                
                # DB 사용 가능시 기존 포지션 확인
                existing_position = None
                if self.db_available and self.position_dao:
                    try:
                        existing_position = self.position_dao.get_position_by_stock(stock_code)
                    except Exception as e:
                        self.logger.warning(f"DB 포지션 조회 실패: {e}")
                
                # 캔들 데이터 가져오기 (30일로 단축)
                self.logger.info(f"캔들 데이터 조회 중: {stock_code} ({stock.get('name', '')})")
                candle_df = self.kiwoom_service.get_daily_candles(stock_code, count=30)
                
                if candle_df.empty or len(candle_df) < 20:
                    self.logger.warning(f"{stock_code}: 캔들 데이터 부족 ({len(candle_df)}일)")
                    enhanced_stock = self._create_basic_stock_data(stock, existing_position)
                    enhanced_stocks.append(enhanced_stock)
                    continue
                
                # 현재 터틀 레벨 계산
                turtle_data = self.turtle_calculator.calculate_current_levels(candle_df, system_type)
                
                if not turtle_data:
                    self.logger.warning(f"{stock_code}: 터틀 계산 실패")
                    enhanced_stock = self._create_basic_stock_data(stock, existing_position)
                    enhanced_stocks.append(enhanced_stock)
                    continue
                
                # DB 사용 가능시만 포지션 관리
                if self.db_available and existing_position:
                    # 기존 포지션: 트레일링 스탑만 업데이트
                    enhanced_stock = await self._update_existing_position(
                        stock, existing_position, turtle_data
                    )
                else:
                    # DB 없거나 신규: 계산된 터틀 데이터만 사용
                    enhanced_stock = self._create_turtle_stock_data(stock, turtle_data)
                
                enhanced_stocks.append(enhanced_stock)
                await asyncio.sleep(0.2)  # API 호출 간격 단축
                
            except Exception as e:
                self.logger.error(f"터틀 데이터 처리 오류 ({stock.get('code', '')}): {e}")
                enhanced_stock = self._create_basic_stock_data(stock, None)
                enhanced_stocks.append(enhanced_stock)
        
        return enhanced_stocks
    
    def _create_basic_stock_data(self, stock: Dict[str, str], position: Optional[TurtlePosition]) -> Dict[str, str]:
        """기본 주식 데이터 생성"""
        enhanced_stock = stock.copy()
        
        if position:
            # 기존 포지션이 있으면 저장된 값 사용
            enhanced_stock.update({
                'stop_loss': float(position.fixed_stop_loss),
                'trailing_stop': float(position.current_trailing_stop) if position.current_trailing_stop else None,
                'add_position': float(position.current_add_position) if position.current_add_position else None,
                'atr_20': float(position.entry_atr),
                'entry_date': position.entry_date.strftime('%Y-%m-%d'),
                'entry_price': float(position.entry_price),
                'position_id': position.id
            })
        else:
            # 포지션 없으면 None
            enhanced_stock.update({
                'stop_loss': None,
                'trailing_stop': None,
                'add_position': None,
                'atr_20': None,
                'entry_date': None,
                'entry_price': None,
                'position_id': None
            })
        
        return enhanced_stock
    
    def _create_turtle_stock_data(self, stock: Dict[str, str], turtle_data: Dict) -> Dict[str, str]:
        """DB 없이 계산된 터틀 데이터만으로 주식 데이터 생성"""
        enhanced_stock = stock.copy()
        
        current_price = turtle_data.get('current_price')
        atr_20 = turtle_data.get('atr_20')
        
        # 터틀 계산 결과 추가
        enhanced_stock.update({
            'stop_loss': current_price - (2 * atr_20),  # 손절가
            'trailing_stop': turtle_data.get('trailing_stop'),  # 트레일링 스탑
            'add_position': turtle_data.get('add_position'),  # 추가매수가
            'atr_20': atr_20,
            'entry_date': None,  # DB 없으므로 None
            'entry_price': None,  # DB 없으므로 None
            'position_id': None   # DB 없으므로 None
        })
        
        return enhanced_stock
    
    async def _update_existing_position(self, stock: Dict[str, str], position: TurtlePosition, 
                                       turtle_data: Dict) -> Dict[str, str]:
        """기존 포지션 업데이트 (트레일링 스탑만)"""
        stock_code = stock.get('code', '')
        
        # 트레일링 스탑과 추가매수가 업데이트
        new_trailing_stop = turtle_data.get('trailing_stop')
        new_add_position = turtle_data.get('add_position')
        
        # DB 업데이트 시도
        try:
            if self.db_available and self.position_dao:
                self.position_dao.update_trailing_stop(
                    position.id, 
                    Decimal(str(new_trailing_stop)),
                    Decimal(str(new_add_position))
                )
                self.logger.info(f"{stock_code}: 포지션 업데이트 - 트레일링: {new_trailing_stop}")
        except Exception as e:
            self.logger.warning(f"포지션 업데이트 실패 ({stock_code}): {e}")
        
        # 기존 포지션 데이터 + 업데이트된 트레일링
        enhanced_stock = stock.copy()
        enhanced_stock.update({
            'stop_loss': float(position.fixed_stop_loss),  # 고정된 손절가
            'trailing_stop': new_trailing_stop,
            'add_position': new_add_position,
            'atr_20': float(position.entry_atr),  # 진입시 ATR
            'entry_date': position.entry_date.strftime('%Y-%m-%d'),
            'entry_price': float(position.entry_price),
            'position_id': position.id
        })
        
        return enhanced_stock
    
    async def _create_new_position(self, stock: Dict[str, str], turtle_data: Dict, 
                                  system_type: int) -> Dict[str, str]:
        """신규 포지션 생성 (DB 사용 가능시만)"""
        
        if not self.db_available or not self.position_dao:
            # DB 없으면 계산된 터틀 데이터만 반환
            return self._create_turtle_stock_data(stock, turtle_data)
        
        stock_code = stock.get('code', '')
        current_price = turtle_data.get('current_price')
        current_atr = turtle_data.get('atr_20')
        
        # 고정 손절가 계산 (진입시 ATR로)
        fixed_stop_loss = current_price - (2 * current_atr)
        
        try:
            # 새 포지션 생성
            new_position = TurtlePosition(
                stock_code=stock_code,
                signal_id=0,  # 조건검색이므로 signal_id는 0
                entry_date=date.today(),
                entry_price=Decimal(str(current_price)),
                entry_atr=Decimal(str(current_atr)),
                fixed_stop_loss=Decimal(str(fixed_stop_loss)),
                system_type=system_type,
                quantity=0,
                current_trailing_stop=Decimal(str(turtle_data.get('trailing_stop'))),
                current_add_position=Decimal(str(turtle_data.get('add_position')))
            )
            
            # DB에 저장
            position_id = self.position_dao.create_position(new_position)
            
            self.logger.info(f"{stock_code}: 신규 포지션 생성 - 진입가: {current_price}, 손절가: {fixed_stop_loss}")
        except Exception as e:
            self.logger.error(f"포지션 저장 실패 ({stock_code}): {e}")
            return self._create_turtle_stock_data(stock, turtle_data)
        
        # 새 포지션 데이터
        enhanced_stock = stock.copy()
        enhanced_stock.update({
            'stop_loss': fixed_stop_loss,
            'trailing_stop': turtle_data.get('trailing_stop'),
            'add_position': turtle_data.get('add_position'),
            'atr_20': current_atr,
            'entry_date': date.today().strftime('%Y-%m-%d'),
            'entry_price': current_price,
            'position_id': position_id
        })
        
        return enhanced_stock

    async def collect_condition_results(self) -> Dict[str, List[Dict[str, str]]]:
        """조건검색 결과 수집 (각 조건식 독립 처리)"""
        self.logger.info("=== 조건검색 결과 수집 시작 ===")
        try:
            seq_results: Dict[str, List[Dict[str, str]]] = {}
            system_results: Dict[str, List[Dict[str, str]]] = {"1": [], "2": []}
            
            total_conditions = len(self.condition_sequences)
            for idx, seq in enumerate(self.condition_sequences, 1):
                try:
                    self.logger.info(f"📊 조건식 {seq} 결과 조회 시작 ({idx}/{total_conditions})")
                    
                    # WebSocket 연결 안정화를 위한 대기
                    if idx > 1:  # 첫 번째 조건식이 아니면 대기
                        self.logger.info(f"⏳ WebSocket 안정화 대기 (3초)...")
                        await asyncio.sleep(3)
                    
                    results = await self.kiwoom_service.request_condition(seq)
                    seq_results[seq] = results
                    
                    if not results:
                        self.logger.warning(f"⚠️ 조건식 {seq}: 결과가 없습니다")
                        continue
                    
                    # seq를 시스템으로 매핑하여 결과 분류
                    system = self.system_seq_mapping.get(seq, seq)
                    
                    # 종목 수 제한 (각 시스템당 최대 20개로 더 축소)
                    max_stocks = 20
                    limited_results = results[:max_stocks] if len(results) > max_stocks else results
                    
                    if len(results) > max_stocks:
                        self.logger.warning(f"📊 조건식 {seq}: {len(results)}개 → {max_stocks}개로 제한")
                    
                    # 각 종목의 손절가/익절가 계산 (시간 단축을 위해 간소화)
                    try:
                        enhanced_results = await self._enhance_with_turtle_data(limited_results, int(system))
                        
                        if system in system_results:
                            system_results[system].extend(enhanced_results)
                        
                        self.logger.info(f"✅ 조건식 {seq} (System {system}): {len(enhanced_results)}개 종목 처리 완료")
                        
                        # 상위 3개 종목 로깅
                        for i, stock in enumerate(enhanced_results[:3]):
                            current = stock.get('current', 0)
                            self.logger.info(f"  🏆 {i+1}. {stock.get('code')} {stock.get('name')} - 현재가: {current:,}원")
                        
                        if len(enhanced_results) > 3:
                            self.logger.info(f"  📈 ... 외 {len(enhanced_results) - 3}개 종목")
                            
                    except Exception as enhance_error:
                        self.logger.error(f"❌ 조건식 {seq} 터틀 계산 실패: {enhance_error}")
                        # 터틀 계산 실패해도 기본 결과는 저장
                        if system in system_results:
                            system_results[system].extend(limited_results)
                    
                except Exception as e:
                    self.logger.error(f"❌ 조건식 {seq} 전체 처리 실패: {e}")
                    seq_results[seq] = []
                    # 실패해도 다음 조건식 계속 처리
                    continue
            
            # 최종 결과 요약
            total = sum(len(v) for v in system_results.values())
            self.logger.info(f"🎯 === 조건검색 완료: 총 {total}개 종목 ===")
            self.logger.info(f"   📊 System 1: {len(system_results['1'])}개")
            self.logger.info(f"   📊 System 2: {len(system_results['2'])}개")
            
            await self.save_condition_results(seq_results)
            return system_results
            
        except Exception as e:
            self.logger.error(f"❌ collect_condition_results 전체 오류: {e}")
            return {"1": [], "2": []}

    async def save_condition_results(self, results: Dict[str, List[Dict[str, str]]]) -> None:
        """결과 저장 (로그 또는 DB)"""
        kst_now = self.get_kst_now()
        ts = kst_now.strftime('%Y-%m-%d %H:%M:%S KST')
        self.logger.info(f"조건검색 결과 저장 시작: {ts}")
        for seq, stocks in results.items():
            self.logger.info(f"조건식 {seq}: {len(stocks)}개 저장")
            # TODO: DB 저장 로직
        self.logger.info("조건검색 결과 저장 완료")

    def run_condition_collection(self) -> Dict[str, List[Dict[str, str]]]:
        """동기 호출 래퍼"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.collect_condition_results())
            loop.close()
            return result
        except Exception as e:
            self.logger.error(f"run_condition_collection 오류: {e}")
            return {"1": [], "2": []}

    def start_scheduler(self) -> None:
        """스케줄러 시작 (백그라운드 루프 실행)"""
        schedule.every().day.at("16:00").do(self.run_condition_collection)
        kst_now = self.get_kst_now()
        self.logger.info(f"스케줄러 등록 완료: 매일 KST 16:00 실행 (현재: {kst_now.strftime('%Y-%m-%d %H:%M:%S KST')})")
        # 초기 실행
        self.run_condition_collection()
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                self.logger.error(f"스케줄러 루프 오류: {e}")
                time.sleep(60)

    def fetch_turtle_signals(self) -> Dict[str, List[Dict[str, str]]]:
        """외부 호출용: 즉시 조건검색 실행"""
        return self.run_condition_collection()


def start_scheduler_thread() -> threading.Thread:
    """
    DailyScheduler.start_scheduler를 데몬 스레드로 실행
    """
    scheduler = DailyScheduler()
    thread = threading.Thread(
        target=scheduler.start_scheduler,
        name="TurtleSchedulerThread",
        daemon=True
    )
    thread.start()
    logger.info("Scheduler thread started")
    return thread
