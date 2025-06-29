import logging
from flask import Flask
from api.routes import api_bp, main_bp
from scheduler.turtle_scheduler import start_scheduler_thread

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    logger.info("터틀 대시보드 앱 생성 중...")
    
    # Blueprint 등록
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 스케줄러 시작
    start_scheduler_thread()
    
    logger.info("터틀 대시보드 앱 설정 완료")
    return app

# Flask 앱 생성 (gunicorn 접근용)
app = create_app()

if __name__ == '__main__':
    logger.info("터틀 대시보드 개발 서버 시작")
    app.run(debug=True, host='0.0.0.0', port=5000)
