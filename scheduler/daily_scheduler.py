# scheduler/daily_scheduler.py

import schedule
import time
import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from services.kiwoom_service import KiwoomAPIService
from config import Config

logger = logging.getLogger(__name__)

class DailyScheduler:
    def __init__(self):
        self.kiwoom_service = KiwoomAPIService()
        self.logger = logging.getLogger(__name__)
        
        # 조건검색 seq 번호들 (실제 사용할 조건식 번호들로 설정)
        self.condition_sequences = [
            "1",  # 첫 번째 조건식
            "2",  # 두 번째 조건식
            # 필요한 만큼 추가
        ]
    
    async def collect_condition_results(self):
        """조건검색 결과 수집"""
        self.logger.info("=== 조건검색 결과 수집 시작 ===")
        
        try:
            all_results = {}
            
            for seq in self.condition_sequences:
                try:
                    self.logger.info(f"조건식 {seq} 결과 조회 시작")
                    
                    # 조건검색 실행
                    condition_results = await self.kiwoom_service.request_condition(seq)
                    
                    all_results[seq] = condition_results
                    self.logger.info(f"조건식 {seq}: {len(condition_results)}개 종목 조회 완료")
                    
                    # 결과 로깅 (상위 5개만)
                    for i, stock in enumerate(condition_results[:5]):
                        self.logger.info(f"  {i+1}. {stock.get('code')} {stock.get('name')} - 현재가: {stock.get('current')}")
                    
                    if len(condition_results) > 5:
                        self.logger.info(f"  ... 외 {len(condition_results) - 5}개 종목")
                    
                    # API 호출 간격 (필요시)
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"조건식 {seq} 조회 실패: {e}")
                    all_results[seq] = []
                    continue
            
            # 전체 결과 요약
            total_stocks = sum(len(results) for results in all_results.values())
            self.logger.info(f"=== 조건검색 수집 완료: 총 {total_stocks}개 종목 ===")
            
            # 여기서 결과를 데이터베이스에 저장하거나 추가 처리
            await self.save_condition_results(all_results)
            
            return all_results
            
        except Exception as e:
            self.logger.error(f"조건검색 결과 수집 실패: {e}")
            return {}
    
    async def save_condition_results(self, results: Dict[str, List[Dict[str, str]]]):
        """조건검색 결과 저장 (추후 데이터베이스 연동)"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 임시로 로그에 저장 (나중에 DB 저장으로 변경)
            self.logger.info(f"조건검색 결과 저장 시작 - {timestamp}")
            
            for seq, stock_list in results.items():
                if stock_list:
                    self.logger.info(f"조건식 {seq}: {len(stock_list)}개 종목 저장")
                    
                    # TODO: 실제 데이터베이스 저장 로직
                    # self.db_handler.save_condition_results(seq, stock_list, timestamp)
            
            self.logger.info("조건검색 결과 저장 완료")
            
        except Exception as e:
            self.logger.error(f"조건검색 결과 저장 실패: {e}")
    
    def run_condition_collection(self):
        """동기 함수에서 비동기 함수 실행"""
        try:
            # 새로운 이벤트 루프 생성 및 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self.collect_condition_results())
            
            loop.close()
            return result
            
        except Exception as e:
            self.logger.error(f"조건검색 실행 오류: {e}")
            return {}
    
    def start_scheduler(self):
        """스케줄러 시작"""
        # 매일 오후 4시에 조건검색 실행
        schedule.every().day.at("16:00").do(self.run_condition_collection)
        
        # 테스트용: 매 10분마다 실행 (개발/테스트시에만 사용)
        # schedule.every(10).minutes.do(self.run_condition_collection)
        
        self.logger.info("조건검색 스케줄러 시작 - 매일 16:00에 실행")
        
        # 시작 시 한 번 실행 (테스트용)
        self.logger.info("초기 조건검색 실행")
        self.run_condition_collection()
        
        # 스케줄 실행 루프
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
            except KeyboardInterrupt:
                self.logger.info("스케줄러 중지")
                break
            except Exception as e:
                self.logger.error(f"스케줄러 실행 오류: {e}")
                time.sleep(60)
    
    def fetch_turtle_signals(self):
        """기존 메서드 호환성을 위한 래퍼"""
        self.logger.info("fetch_turtle_signals 호출 - 조건검색 실행")
        return self.run_condition_collection()

def run_scheduler():
    """스케줄러 실행 함수 (별도 스레드용)"""
    scheduler = DailyScheduler()
    scheduler.start_scheduler()