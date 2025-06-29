import schedule
import time
from datetime import datetime
import logging
import threading

from services.kiwoom_service import KiwoomAPIService
from services.turtle_calculator import TurtleCalculator
from database.database_handler import DatabaseHandler
from config import Config

class DailyScheduler:
    def __init__(self):
        self.kiwoom_service = KiwoomAPIService(
            Config.KIWOOM_APP_KEY,
            Config.KIWOOM_APP_SECRET,
            Config.KIWOOM_BASE_URL
        )
        self.db_handler = DatabaseHandler()
        self.turtle_calculator = TurtleCalculator()
        self.logger = logging.getLogger(__name__)
        
        # 수집 대상 종목 (나중에 DB에서 관리)
        self.target_stocks = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # NAVER
            "005380",  # 현대차
            "006400",  # 삼성SDI
            "051910",  # LG화학
            "028260",  # 삼성물산
            "068270",  # 셀트리온
            "035720",  # 카카오
            "207940",  # 삼성바이오로직스
        ]
    
    def daily_data_collection_and_analysis(self):
        """일일 데이터 수집 및 터틀 신호 분석"""
        self.logger.info("=== 일일 데이터 수집 및 터틀 분석 시작 ===")
        
        try:
            # 1단계: 캔들 데이터 수집
            self.collect_candle_data()
            
            # 2단계: 터틀 신호 계산
            self.calculate_turtle_signals()
            
            self.logger.info("=== 일일 작업 완료 ===")
            
        except Exception as e:
            self.logger.error(f"일일 작업 실패: {e}")
    
    def collect_candle_data(self):
        """캔들 데이터 수집"""
        self.logger.info("캔들 데이터 수집 시작")
        
        all_candle_data = []
        
        for stock_code in self.target_stocks:
            try:
                # 최근 5일 데이터 조회 (누락 데이터 보완)
                candle_data = self.kiwoom_service.get_daily_candle_data(stock_code, 5)
                all_candle_data.extend(candle_data)
                
                # API 호출 제한 준수
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"{stock_code} 데이터 수집 실패: {e}")
                continue
        
        # 데이터베이스 업데이트
        if all_candle_data:
            self.db_handler.upsert_candle_data(all_candle_data)
            self.logger.info(f"총 {len(all_candle_data)}개 캔들 데이터 수집 완료")
    
    def calculate_turtle_signals(self):
        """터틀 신호 계산 및 저장"""
        self.logger.info("터틀 신호 계산 시작")
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        all_signals = []
        
        # 활성 종목들에 대해 터틀 신호 계산
        active_stocks = self.db_handler.get_all_active_stocks()
        
        for stock_code in active_stocks:
            try:
                # 60일 캔들 데이터 조회 (터틀 계산용)
                df = self.db_handler.get_candle_data_for_turtle(stock_code, 60)
                
                if df.empty or len(df) < 30:
                    continue
                
                # 시스템 1 신호 계산
                signal1 = self.turtle_calculator.calculate_turtle_system1(df, current_date)
                if signal1:
                    signal1.stock_code = stock_code
                    all_signals.append(signal1)
                
                # 시스템 2 신호 계산
                signal2 = self.turtle_calculator.calculate_turtle_system2(df, current_date)
                if signal2:
                    signal2.stock_code = stock_code
                    all_signals.append(signal2)
                
            except Exception as e:
                self.logger.error(f"{stock_code} 터틀 신호 계산 실패: {e}")
                continue
        
        # 터틀 신호 저장
        if all_signals:
            self.db_handler.save_turtle_signals(all_signals)
            self.logger.info(f"총 {len(all_signals)}개 터틀 신호 저장 완료")
    
    def start_scheduler(self):
        """스케줄러 시작"""
        # 매일 오후 4시에 실행
        schedule.every().day.at(Config.DATA_COLLECTION_TIME).do(
            self.daily_data_collection_and_analysis
        )
        
        # 테스트용: 매 5분마다 실행 (개발 시에만 사용)
        # schedule.every(5).minutes.do(self.daily_data_collection_and_analysis)
        
        self.logger.info(f"스케줄러 시작 - 매일 {Config.DATA_COLLECTION_TIME}에 실행")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크

def run_scheduler():
    """스케줄러 실행 함수 (별도 스레드용)"""
    scheduler = DailyScheduler()
    scheduler.start_scheduler()