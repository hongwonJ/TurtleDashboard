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
        # 조건검색 seq 번호들을 동적으로 찾기
        self.condition_sequences = []
        self.system_seq_mapping = {}  # seq -> system name 매핑
        self._initialize_system_sequences()

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

    async def collect_condition_results(self) -> Dict[str, List[Dict[str, str]]]:
        """조건검색 결과 수집"""
        self.logger.info("=== 조건검색 결과 수집 시작 ===")
        try:
            seq_results: Dict[str, List[Dict[str, str]]] = {}
            system_results: Dict[str, List[Dict[str, str]]] = {"1": [], "2": []}
            
            for seq in self.condition_sequences:
                try:
                    self.logger.info(f"조건식 {seq} 결과 조회 시작")
                    results = await self.kiwoom_service.request_condition(seq)
                    seq_results[seq] = results
                    
                    # seq를 시스템으로 매핑하여 결과 분류
                    system = self.system_seq_mapping.get(seq, seq)
                    if system in system_results:
                        system_results[system].extend(results)
                    
                    self.logger.info(f"조건식 {seq} (System {system}): {len(results)}개 종목 조회 완료")
                    for i, stock in enumerate(results[:5]):
                        self.logger.info(
                            f"  {i+1}. {stock.get('code')} {stock.get('name')} - 현재가: {stock.get('current')}"
                        )
                    if len(results) > 5:
                        self.logger.info(f"  ... 외 {len(results) - 5}개 종목")
                    await asyncio.sleep(1)
                except Exception as e:
                    self.logger.error(f"조건식 {seq} 조회 실패: {e}")
                    seq_results[seq] = []
            
            total = sum(len(v) for v in system_results.values())
            self.logger.info(f"=== 총 {total}개 종목 조회 완료 (System 1: {len(system_results['1'])}개, System 2: {len(system_results['2'])}개) ===")
            await self.save_condition_results(seq_results)
            return system_results
        except Exception as e:
            self.logger.error(f"collect_condition_results 오류: {e}")
            return {"1": [], "2": []}

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
            return {"1": [], "2": []}

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
