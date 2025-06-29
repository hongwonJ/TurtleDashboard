import logging
from flask import Flask, jsonify

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    logger.info("Flask 앱 생성 중...")
    
    @app.route('/')
    def index():
        logger.info("메인 페이지 요청")
        return '''
        <h1>🐢 터틀 대시보드</h1>
        <p>앱이 정상적으로 작동 중입니다!</p>
        <ul>
            <li><a href="/api/health">헬스 체크</a></li>
            <li><a href="/api/test">환경변수 테스트</a></li>
            <li><a href="/api/test-db">DB 연결 테스트</a></li>
        </ul>
        '''
    
    @app.route('/api/health')
    def health():
        logger.info("헬스 체크 요청")
        return jsonify({
            'status': 'ok',
            'message': 'Flask 앱이 정상 작동 중'
        })
    
    @app.route('/api/test')
    def test():
        logger.info("환경변수 테스트 요청")
        try:
            import os
            env_vars = {
                'AZURE_MYSQL_HOST': os.getenv('AZURE_MYSQL_HOST', 'NOT_SET'),
                'AZURE_MYSQL_NAME': os.getenv('AZURE_MYSQL_NAME', 'NOT_SET'),
                'AZURE_MYSQL_USER': os.getenv('AZURE_MYSQL_USER', 'NOT_SET'),
                'AZURE_MYSQL_PASSWORD': '***' if os.getenv('AZURE_MYSQL_PASSWORD') else 'NOT_SET'
            }
            return jsonify({
                'status': 'success',
                'environment_variables': env_vars
            })
        except Exception as e:
            logger.error(f"테스트 실패: {e}")
            return jsonify({'status': 'error', 'message': str(e)})
    
    @app.route('/api/test-db')
    def test_db():
        logger.info("DB 연결 테스트 요청")
        try:
            # 연결 정보 먼저 확인
            import os
            host = os.getenv('AZURE_MYSQL_HOST')
            username = os.getenv('AZURE_MYSQL_USER')
            
            # Azure MySQL 사용자명 형식 확인
            if '@' not in username and host:
                server_name = host.split('.')[0]
                full_username = f"{username}@{server_name}"
            else:
                full_username = username
            
            logger.info(f"연결 시도: {full_username}@{host}")
            
            # DB 연결 테스트
            from database.connection import DatabaseConnection
            db_conn = DatabaseConnection()
            conn = db_conn.get_connection()
            
            # 간단한 쿼리 실행
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            logger.info("DB 연결 성공!")
            return jsonify({
                'status': 'success',
                'message': 'DB 연결 성공',
                'username_used': full_username,
                'test_query_result': result[0] if result else None
            })
            
        except Exception as e:
            logger.error(f"DB 연결 실패: {e}")
            return jsonify({
                'status': 'error', 
                'message': f'DB 연결 실패: {str(e)}',
                'username_attempted': full_username if 'full_username' in locals() else username,
                'host': host
            })
    
    logger.info("Flask 앱 설정 완료")
    return app

# gunicorn이 찾을 수 있도록 모듈 레벨에 app 노출
app = create_app()
logger.info('터틀 대시보드 앱 시작 완료')

if __name__ == '__main__':
    logger.info('Starting Flask application in development mode')
    app.run(debug=True, host='0.0.0.0', port=8000)
