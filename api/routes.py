from flask import Blueprint, render_template, jsonify
import logging
from datetime import datetime

from scheduler.daily_scheduler import DailyScheduler
from database.position_dao import PositionDAO

logger = logging.getLogger(__name__)

# Blueprint 생성
api_bp = Blueprint('api', __name__)
main_bp = Blueprint('main', __name__)


def get_turtle_data():
    """
    DB에서 활성 포지션 데이터를 가져와서 시스템별로 분류하여 반환
    DB 연결 실패시 빈 데이터 반환
    """
    try:
        position_dao = PositionDAO()
        active_positions = position_dao.get_active_positions()
        
        # 시스템별로 분류
        system1 = []
        system2 = []
        
        for position in active_positions:
            # 포지션 데이터를 웹페이지 형식으로 변환
            stock_data = {
                'code': position.stock_code,
                'name': f'종목{position.stock_code}',  # 종목명은 별도 조회 필요
                'current': None,  # 현재가는 실시간 API 필요
                'rate': None,     # 등락률도 실시간 API 필요
                'volume': None,   # 거래량도 실시간 API 필요
                'stop_loss': float(position.fixed_stop_loss),
                'trailing_stop': float(position.current_trailing_stop) if position.current_trailing_stop else None,
                'add_position': float(position.current_add_position) if position.current_add_position else None,
                'entry_date': position.entry_date.strftime('%Y-%m-%d'),
                'entry_price': float(position.entry_price),
                'position_id': position.id
            }
            
            if position.system_type == 1:
                system1.append(stock_data)
            else:
                system2.append(stock_data)
        
        logger.info(f"DB에서 포지션 조회 성공: System1={len(system1)}, System2={len(system2)}")
        
        # 마지막 업데이트 시각
        last_updated = datetime.now()
        
        return {
            'system1': system1,
            'system2': system2,
            'last_updated': last_updated
        }
        
    except Exception as e:
        logger.error(f"포지션 데이터 조회 실패: {e}")
        logger.warning("DB 연결 문제로 빈 데이터를 반환합니다.")
        return {
            'system1': [],
            'system2': [],
            'last_updated': datetime.now()
        }


@main_bp.route('/')
def index():
    """메인 페이지 - 시스템별 터틀 신호 종목 리스트와 마지막 업데이트 시각 렌더링"""
    data = get_turtle_data()
    return render_template(
        'index.html',
        system1_stocks=data['system1'],
        system2_stocks=data['system2'],
        last_updated=data['last_updated'].strftime('%Y-%m-%d %H:%M:%S')
    )


@api_bp.route('/turtle-data')
def api_turtle_data():
    """터틀 데이터 API - JSON 형식으로 시스템별 종목 리스트와 마지막 업데이트 시각 제공"""
    data = get_turtle_data()
    return jsonify({
        'system1': data['system1'],
        'system2': data['system2'],
        'last_updated': data['last_updated'].isoformat()
    })


@api_bp.route('/health')
def health():
    """헬스 체크 API"""
    try:
        # DB 연결 테스트
        position_dao = PositionDAO()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    return jsonify({
        'status': 'ok',
        'database': db_status,
        'timestamp': datetime.now().isoformat()
    })

@api_bp.route('/refresh')
def refresh():
    """데이터 새로고침 엔드포인트 - 테스트/디버깅용"""
    try:
        scheduler = DailyScheduler()
        # 직접 동기 호출
        scheduler.fetch_turtle_signals()
        return jsonify({'status': 'success', 'message': '데이터 새로고침 완료'})
    except Exception as e:
        logger.error(f"새로고침 오류: {e}")
        return jsonify({'status': 'error', 'message': str(e)})
