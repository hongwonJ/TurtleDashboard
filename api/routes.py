from flask import Blueprint, render_template, jsonify
import logging
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from scheduler.daily_scheduler import DailyScheduler

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

def update_turtle_data():
    """실제 키움 API 터틀 데이터 업데이트"""
    global turtle_data_store
    
    kst_now = get_kst_now()
    logger.info(f"🚀 터틀 데이터 업데이트 시작 [{kst_now.strftime('%Y-%m-%d %H:%M:%S KST')}]")
    
    try:
        # DailyScheduler 초기화
        turtle_data_store['status'] = 'initializing'
        scheduler = None
        
        try:
            scheduler = DailyScheduler()
            logger.info("📡 DailyScheduler 초기화 완료")
        except Exception as init_error:
            logger.error(f"DailyScheduler 초기화 실패: {init_error}")
            raise Exception(f"Scheduler initialization failed: {init_error}")
        
        # 키움 API 호출
        turtle_data_store['status'] = 'collecting'
        logger.info("📡 키움 API 조건검색 실행 중...")
        
        try:
            results = scheduler.fetch_turtle_signals()
            
            if not isinstance(results, dict):
                raise Exception(f"Invalid results format: {type(results)}")
                
        except Exception as api_error:
            logger.error(f"키움 API 호출 실패: {api_error}")
            raise Exception(f"Kiwoom API call failed: {api_error}")
        
        # 데이터 검증 및 저장
        try:
            system1_data = results.get('1', []) if results else []
            system2_data = results.get('2', []) if results else []
            
            # 데이터 타입 검증
            if not isinstance(system1_data, list):
                system1_data = []
            if not isinstance(system2_data, list):
                system2_data = []
            
            # 데이터 저장
            turtle_data_store['system1'] = system1_data
            turtle_data_store['system2'] = system2_data
            turtle_data_store['last_updated'] = kst_now
            turtle_data_store['status'] = 'updated'
            
            logger.info(f"✅ 터틀 데이터 업데이트 완료: System1={len(system1_data)}개, System2={len(system2_data)}개")
            
            # 안전한 결과 요약 로그
            for i, stock in enumerate(system1_data[:3]):
                if isinstance(stock, dict):
                    current = stock.get('current', 0)
                    logger.info(f"  System1 [{i+1}] {stock.get('code', 'N/A')} {stock.get('name', 'N/A')} - 현재가: {current}")
            for i, stock in enumerate(system2_data[:3]):
                if isinstance(stock, dict):
                    current = stock.get('current', 0)
                    logger.info(f"  System2 [{i+1}] {stock.get('code', 'N/A')} {stock.get('name', 'N/A')} - 현재가: {current}")
                    
        except Exception as save_error:
            logger.error(f"데이터 저장 실패: {save_error}")
            raise Exception(f"Data save failed: {save_error}")
            
    except Exception as e:
        logger.error(f"❌ 터틀 데이터 업데이트 실패: {e}")
        turtle_data_store['status'] = 'error'
        turtle_data_store['system1'] = []
        turtle_data_store['system2'] = []
        turtle_data_store['last_updated'] = kst_now
        raise e  # 상위로 예외 전파

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
        kst_now = get_kst_now()
        logger.info(f"🚀 수동 업데이트 요청 [{kst_now.strftime('%H:%M:%S')}]")
        
        # 안전한 업데이트 호출
        try:
            update_turtle_data()
        except Exception as update_error:
            logger.error(f"업데이트 중 오류 발생: {update_error}")
            return jsonify({
                'status': 'error',
                'message': 'Update failed - check server logs',
                'data_status': 'error',
                'system1_count': 0,
                'system2_count': 0
            })
        
        status = turtle_data_store.get('status', 'unknown')
        if status == 'updated':
            message = 'Update completed successfully'
        elif status == 'error':
            message = 'Kiwoom API call failed'
        else:
            message = f'Status: {status}'
            
        return jsonify({
            'status': 'success',
            'message': message,
            'data_status': status,
            'system1_count': len(turtle_data_store.get('system1', [])),
            'system2_count': len(turtle_data_store.get('system2', []))
        })
    except Exception as e:
        logger.error(f"Manual update failed: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Server error occurred',
            'data_status': 'error',
            'system1_count': 0,
            'system2_count': 0
        })
