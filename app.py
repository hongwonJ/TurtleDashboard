import logging
import schedule
import time
import threading
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from flask import Flask
from api.routes import api_bp, main_bp, update_turtle_data

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = ZoneInfo("Asia/Seoul")

def start_daily_scheduler():
    """매일 오후 4시 터틀 데이터 업데이트 스케줄러"""
    def run_scheduler():
        def scheduled_update():
            kst_now = datetime.now(KST)
            logger.info(f"🕐 스케줄된 터틀 데이터 업데이트 실행: {kst_now.strftime('%Y-%m-%d %H:%M:%S KST')}")
            update_turtle_data()
        
        # 매일 오후 4시에 실행
        schedule.every().day.at("16:00").do(scheduled_update)
        
        kst_now = datetime.now(KST)
        logger.info(f"📅 터틀 스케줄러 등록 완료 - 매일 KST 16:00 실행 (현재: {kst_now.strftime('%Y-%m-%d %H:%M:%S KST')})")
        
        while True:
            schedule.run_pending()
            time.sleep(30)  # 30초마다 체크
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("🚀 터틀 스케줄러 스레드 시작")

def create_app():
    app = Flask(__name__)
    
    # Blueprint 등록
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 스케줄러 시작
    start_daily_scheduler()
    
    logger.info("터틀 대시보드 앱 설정 완료")
    return app

# Flask 앱 생성 (gunicorn 접근용)
app = create_app()

if __name__ == '__main__':
    logger.info("터틀 대시보드 개발 서버 시작")
    app.run(debug=True, host='0.0.0.0', port=5000)
