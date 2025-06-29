import logging
from flask import Flask
from scheduler.daily_scheduler import start_scheduler_thread
from api.routes import api_bp, main_bp

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    # Blueprint 등록
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    return app

if __name__ == '__main__':
    # 스케줄러 헬퍼 함수로 스레드 시작
    start_scheduler_thread()
    logger.info('Turtle Scheduler thread started')

    app = create_app()
    logger.info('Starting Flask application')
    app.run(debug=True, host='0.0.0.0', port=8000)
