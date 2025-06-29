import schedule
import time
import asyncio
import threading
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
        # 조건검색 seq 번호들
        self.condition_sequences = ["6", "7"]

    async def collect_condition_results(self) -> Dict[str, List[Dict[str, str]]]:
        """조건검색 결과 수집"""
        self.logger.info("=== 조건검색 결과 수집 시작 ===")
        try:
            all_results: Dict[str, List[Dict[str, str]]] = {}
            for seq in self.condition_sequences:
                try:
                    self.logger.info(f"조건식 {seq} 결과 조회 시작")
                    results = await self.kiwoom_service.request_condition(seq)
                    all_results[seq] = results
                    self.logger.info(f"조건식 {seq}: {len(results)}개 종목 조회 완료")
                    for i, stock in enumerate(results[:5]):
                        self.logger.info(
                            f"  {i+1}. {stock.get('code')} {stock.get('name')} - 현재가: {stock.get('current')}"
                        )
                    if len(results) > 5:
                        self.logger.info(f"  ... 외 {len(results) - 5}개 종목")
                    await asyncio.sleep(1)
                except Exception as e:
                    self.logger.error(f"조건식 {seq} 조회 실패: {e}")
                    all_results[seq] = []
            total = sum(len(v) for v in all_results.values())
            self.logger.info(f"=== 총 {total}개 종목 조회 완료 ===")
            await self.save_condition_results(all_results)
            return all_results
        except Exception as e:
            self.logger.error(f"collect_condition_results 오류: {e}")
            return {}

    async def save_condition_results(self, results: Dict[str, List[Dict[str, str]]]) -> None:
        """결과 저장 (로그 또는 DB)"""
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
            return {}

    def start_scheduler(self) -> None:
        """스케줄러 시작 (백그라운드 루프 실행)"""
        schedule.every().day.at("16:00").do(self.run_condition_collection)
        self.logger.info("스케줄러 등록 완료: 매일 16:00 실행")
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
