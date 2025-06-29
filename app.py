# app.py

from flask import Flask
import logging
from scheduler import start_scheduler_thread
from api.routes import api_bp, main_bp

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Blueprint 등록
app.register_blueprint(main_bp)
app.register_blueprint(api_bp, url_prefix='/api')

if __name__ == '__main__':
    # 스케줄러 시작
    start_scheduler_thread()
    logger.info("터틀 대시보드 웹 애플리케이션 시작")
    
    # Flask 애플리케이션 실행
    app.run(debug=True, host='0.0.0.0', port=8000)