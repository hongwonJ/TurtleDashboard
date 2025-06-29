import threading
import schedule
import time
import logging

logger = logging.getLogger(__name__)

def start_scheduler_thread():
    """스케줄러를 별도 스레드에서 시작"""
    def run_scheduler():
        # 매일 오후 4시에 실행
        from api.routes import mock_turtle_scheduler
        schedule.every().day.at("16:00").do(mock_turtle_scheduler)
        
        # 테스트용: 매 5분마다 실행 (개발 중에만)
        # schedule.every(5).minutes.do(mock_turtle_scheduler)
        
        logger.info("터틀 스케줄러 등록 완료 - 매일 오후 4시 실행")
        
        while True:
            schedule.run_pending()
            time.sleep(30)  # 30초마다 체크
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("터틀 스케줄러 스레드 시작") 