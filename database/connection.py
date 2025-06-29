# DB 연결 관리 파일
import mysql.connector
from mysql.connector import pooling
import logging
from config import Config

class DatabaseConnection:
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self):
        """Azure MySQL 서버용 커넥션 풀 초기화"""
        try:
            config = {
                'user': Config.DB_USERNAME,
                'password': Config.DB_PASSWORD,
                'host': Config.DB_HOST,
                'port': Config.DB_PORT,
                'database': Config.DB_DATABASE,
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'autocommit': False,
                'pool_name': 'turtle_pool',
                'pool_size': 10,
                'pool_reset_session': True
            }
            self._pool = pooling.MySQLConnectionPool(**config)
            logging.info("Azure MySQL 커넥션 풀 초기화 완료")
        except Exception as e:
            logging.error(f"Azure MySQL 커넥션 풀 초기화 실패: {e}")
            raise
    
    def get_connection(self):
        """커넥션 풀에서 연결 반환"""
        try:
            return self._pool.get_connection()
        except Exception as e:
            logging.error(f"데이터베이스 연결 실패: {e}")
            raise
