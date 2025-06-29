from flask import Blueprint, render_template, jsonify
import logging
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from scheduler.daily_scheduler import DailyScheduler
from database.position_dao import PositionDAO

logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = ZoneInfo("Asia/Seoul")

def get_kst_now():
    """KST 기준 현재 시간 반환"""
    return datetime.now(KST)

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

def real_turtle_scheduler():
    """🔥 실제 키움 API 터틀 스케줄러"""
    global turtle_data_store
    
    kst_now = get_kst_now()
    logger.info(f"🚀 실제 키움 API 터틀 스케줄러 실행! [{kst_now.strftime('%Y-%m-%d %H:%M:%S KST')}]")
    
    try:
        # 실제 DailyScheduler 사용
        scheduler = DailyScheduler()
        turtle_data_store['status'] = 'collecting'
        
        # 키움 API에서 실제 조건검색 결과 수집
        logger.info("📡 키움 API 조건검색 실행 중...")
        results = scheduler.fetch_turtle_signals()
        
        # System 별로 데이터 저장
        system1_data = results.get('1', [])
        system2_data = results.get('2', [])
        
        # 데이터 저장
        turtle_data_store['system1'] = system1_data
        turtle_data_store['system2'] = system2_data
        turtle_data_store['last_updated'] = kst_now
        turtle_data_store['status'] = 'updated'
        
        logger.info(f"✅ 실제 터틀 데이터 업데이트 완료: System1={len(system1_data)}개, System2={len(system2_data)}개")
        
        # 결과 요약 로그
        for i, stock in enumerate(system1_data[:3]):
            logger.info(f"  System1 [{i+1}] {stock.get('code')} {stock.get('name')} - 현재가: {stock.get('current'):,}원")
        for i, stock in enumerate(system2_data[:3]):
            logger.info(f"  System2 [{i+1}] {stock.get('code')} {stock.get('name')} - 현재가: {stock.get('current'):,}원")
            
    except Exception as e:
        logger.error(f"❌ 실제 키움 API 호출 실패: {e}")
        turtle_data_store['status'] = 'error'
        
        # 에러 시 Mock 데이터로 대체
        logger.warning("⚠️  키움 API 실패로 Mock 데이터 사용")
        mock_fallback_data()

def mock_fallback_data():
    """키움 API 실패시 대체 Mock 데이터"""
    global turtle_data_store
    
    import random
    
    # 간단한 Mock 데이터
    real_stocks = [
        {"code": "005930", "name": "삼성전자", "price": 70000, "atr": 1500},
        {"code": "000660", "name": "SK하이닉스", "price": 100000, "atr": 3000},
        {"code": "035420", "name": "NAVER", "price": 175000, "atr": 4500}
    ]
    
    system1_data = []
    system2_data = []
    
    for i, stock_info in enumerate(real_stocks):
        if i < 2:  # System 1
            system1_data.append({
                'code': stock_info["code"],
                'name': stock_info["name"],
                'entry_date': get_kst_now().strftime('%Y-%m-%d'),
                'entry_price': stock_info["price"],
                'current': stock_info["price"] + random.randint(-1000, 1000),
                'stop_loss': stock_info["price"] - (2 * stock_info["atr"]),
                'trailing_stop': stock_info["price"] - random.randint(800, 1200),
                'add_position': stock_info["price"] + (0.5 * stock_info["atr"]),
                'atr_20': stock_info["atr"]
            })
        else:  # System 2
            system2_data.append({
                'code': stock_info["code"],
                'name': stock_info["name"],
                'entry_date': get_kst_now().strftime('%Y-%m-%d'),
                'entry_price': stock_info["price"],
                'current': stock_info["price"] + random.randint(-2000, 2000),
                'stop_loss': stock_info["price"] - (2 * stock_info["atr"]),
                'trailing_stop': stock_info["price"] - random.randint(1500, 2500),
                'add_position': stock_info["price"] + (0.5 * stock_info["atr"]),
                'atr_20': stock_info["atr"]
            })
    
    turtle_data_store['system1'] = system1_data
    turtle_data_store['system2'] = system2_data
    turtle_data_store['last_updated'] = get_kst_now()
    turtle_data_store['status'] = 'mock_fallback'

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
    """🔥 실제 키움 API 수동 업데이트"""
    try:
        kst_now = get_kst_now()
        logger.info(f"🚀 실제 키움 API 수동 업데이트 요청 [{kst_now.strftime('%H:%M:%S')}]")
        real_turtle_scheduler()
        
        status = turtle_data_store.get('status', 'unknown')
        if status == 'updated':
            message = '✅ 실제 키움 API 데이터 업데이트 완료!'
        elif status == 'mock_fallback':
            message = '⚠️ 키움 API 실패로 Mock 데이터 사용'
        else:
            message = f'❌ 업데이트 상태: {status}'
            
        return jsonify({
            'status': 'success',
            'message': message,
            'data_status': status,
            'system1_count': len(turtle_data_store.get('system1', [])),
            'system2_count': len(turtle_data_store.get('system2', []))
        })
    except Exception as e:
        logger.error(f"수동 업데이트 실패: {e}")
        return jsonify({
            'status': 'error',
            'message': f'❌ 업데이트 실패: {str(e)}'
        })
