import logging
from flask import Flask
from scheduler.daily_scheduler import start_scheduler_thread
from api.routes import api_bp, main_bp
from database.handler import DatabaseHandler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # 데이터베이스 테이블 초기화
    try:
        db_handler = DatabaseHandler()
        db_handler.create_tables()
        logger.info("데이터베이스 테이블 초기화 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
    
    # Blueprint 등록
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    return app

# gunicorn이 찾을 수 있도록 모듈 레벨에 app 노출
app = create_app()

# 스케줄러는 앱 생성 후 시작
start_scheduler_thread()
logger.info('Turtle Scheduler thread started')

if __name__ == '__main__':
    logger.info('Starting Flask application in development mode')
    app.run(debug=True, host='0.0.0.0', port=8000)
