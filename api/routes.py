from flask import Blueprint, render_template, jsonify
import logging
from datetime import datetime

from scheduler.daily_scheduler import DailyScheduler
from database.position_dao import PositionDAO

logger = logging.getLogger(__name__)

# Blueprint 생성
api_bp = Blueprint('api', __name__)
main_bp = Blueprint('main', __name__)

# 메모리 저장소 (DB 대신)
turtle_data_store = {
    'system1': [],
    'system2': [],
    'last_updated': None,
    'status': 'waiting'
}

def mock_turtle_scheduler():
    """모의 터틀 스케줄러 (키움 API 대신)"""
    global turtle_data_store
    
    logger.info("오후 4시 터틀 스케줄러 실행!")
    
    # 모의 데이터 생성 (실제로는 키움 API 호출)
    import random
    
    # System 1 (단기) 모의 데이터
    system1_stocks = []
    for i in range(random.randint(3, 8)):
        stock_code = f"00{random.randint(1000, 9999)}"
        current_price = random.randint(10000, 50000)
        atr = random.randint(500, 2000)
        
        # 실제 종목명 예시
        stock_names = ["삼성전자", "SK하이닉스", "NAVER", "카카오", "LG화학", "현대차", "기아", "POSCO홀딩스"]
        stock_name = random.choice(stock_names)
        
        stock_data = {
            'code': stock_code,
            'name': stock_name,
            'entry_date': datetime.now().strftime('%Y-%m-%d'),
            'entry_price': current_price,
            'current': current_price + random.randint(-1000, 1000),
            'stop_loss': current_price - (2 * atr),
            'trailing_stop': current_price - random.randint(800, 1200),
            'add_position': current_price + (0.5 * atr),
            'atr_20': atr
        }
        system1_stocks.append(stock_data)
    
    # System 2 (장기) 모의 데이터  
    system2_stocks = []
    for i in range(random.randint(2, 6)):
        stock_code = f"00{random.randint(1000, 9999)}"
        current_price = random.randint(15000, 80000)
        atr = random.randint(800, 3000)
        
        # 실제 종목명 예시
        stock_names = ["삼성전자", "SK하이닉스", "NAVER", "카카오", "LG화학", "현대차", "기아", "POSCO홀딩스", "셀트리온", "LG에너지솔루션"]
        stock_name = random.choice(stock_names)
        
        stock_data = {
            'code': stock_code,
            'name': stock_name,
            'entry_date': datetime.now().strftime('%Y-%m-%d'),
            'entry_price': current_price,
            'current': current_price + random.randint(-2000, 2000),
            'stop_loss': current_price - (2 * atr),
            'trailing_stop': current_price - random.randint(1500, 2500),
            'add_position': current_price + (0.5 * atr),
            'atr_20': atr
        }
        system2_stocks.append(stock_data)
    
    # 데이터 저장
    turtle_data_store['system1'] = system1_stocks
    turtle_data_store['system2'] = system2_stocks
    turtle_data_store['last_updated'] = datetime.now()
    turtle_data_store['status'] = 'updated'
    
    logger.info(f"터틀 데이터 업데이트 완료: System1={len(system1_stocks)}개, System2={len(system2_stocks)}개")

# 메인 페이지
@main_bp.route('/')
def index():
    """메인 페이지"""
    logger.info("메인 페이지 요청")
    
    # 현재 데이터 가져오기
    system1 = turtle_data_store.get('system1', [])
    system2 = turtle_data_store.get('system2', [])
    last_updated = turtle_data_store.get('last_updated')
    status = turtle_data_store.get('status', 'waiting')
    
    return render_template('index.html', 
                          system1=system1, 
                          system2=system2,
                          last_updated=last_updated,
                          status=status)

# API 엔드포인트
@api_bp.route('/health')
def health():
    """헬스 체크"""
    return jsonify({
        'status': 'ok',
        'message': '터틀 대시보드 정상 작동',
        'data_status': turtle_data_store.get('status', 'waiting'),
        'last_updated': turtle_data_store.get('last_updated').isoformat() if turtle_data_store.get('last_updated') else None
    })

@api_bp.route('/turtle-data')
def turtle_data():
    """터틀 데이터 API"""
    return jsonify({
        'system1': turtle_data_store.get('system1', []),
        'system2': turtle_data_store.get('system2', []),
        'last_updated': turtle_data_store.get('last_updated').isoformat() if turtle_data_store.get('last_updated') else None,
        'status': turtle_data_store.get('status', 'waiting')
    })

@api_bp.route('/manual-update', methods=['POST'])
def manual_update():
    """수동 업데이트"""
    try:
        logger.info("수동 업데이트 요청")
        mock_turtle_scheduler()
        return jsonify({
            'status': 'success',
            'message': '터틀 데이터 수동 업데이트 완료'
        })
    except Exception as e:
        logger.error(f"수동 업데이트 실패: {e}")
        return jsonify({
            'status': 'error',
            'message': f'업데이트 실패: {str(e)}'
        })
