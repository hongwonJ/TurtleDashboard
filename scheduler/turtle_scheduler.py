import threading
import schedule
import time
import logging
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = ZoneInfo("Asia/Seoul")

def start_scheduler_thread():
    """스케줄러를 별도 스레드에서 시작"""
    def run_scheduler():
        # 매일 오후 4시에 실행 (KST 기준)
        from api.routes import real_turtle_scheduler
        
        def kst_turtle_scheduler():
            kst_now = datetime.now(KST)
            logger.info(f"🔥 실제 키움 API 터틀 스케줄러 실행: {kst_now.strftime('%Y-%m-%d %H:%M:%S KST')}")
            real_turtle_scheduler()
        
        schedule.every().day.at("16:00").do(kst_turtle_scheduler)
        
        # 테스트용: 매 5분마다 실행 (개발 중에만)
        # schedule.every(5).minutes.do(kst_turtle_scheduler)
        
        kst_now = datetime.now(KST)
        logger.info(f"터틀 스케줄러 등록 완료 - 매일 KST 오후 4시 실행 (현재: {kst_now.strftime('%Y-%m-%d %H:%M:%S KST')})")
        
        while True:
            schedule.run_pending()
            time.sleep(30)  # 30초마다 체크
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("터틀 스케줄러 스레드 시작") 