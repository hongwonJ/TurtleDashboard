# 설정 파일
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    # 키움 API 설정
    KIWOOM_APP_KEY = os.getenv('KIWOOM_APP_KEY')
    KIWOOM_APP_SECRET = os.getenv('KIWOOM_APP_SECRET')
    KIWOOM_BASE_URL = 'https://api.kiwoom.com'
    KIWOOM_WSS_URL = 'wss://api.kiwoom.com:10000'
    
    # MySQL 데이터베이스 설정 (Azure Web App + Database)
    DB_HOST = os.getenv('AZURE_MYSQL_HOST')
    DB_PORT = 3306  # MySQL 기본 포트
    DB_DATABASE = os.getenv('AZURE_MYSQL_NAME')
    DB_USERNAME = os.getenv('AZURE_MYSQL_USER')
    DB_PASSWORD = os.getenv('AZURE_MYSQL_PASSWORD')
    
    # 스케줄링 설정
    DATA_COLLECTION_TIME = "16:00"  # 오후 4시
    
    # 로깅 설정
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/app.log'
