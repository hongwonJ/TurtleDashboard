from flask import Blueprint, render_template, jsonify
import logging
from datetime import datetime

from scheduler.daily_scheduler import DailyScheduler

logger = logging.getLogger(__name__)

# Blueprint 생성
api_bp = Blueprint('api', __name__)
main_bp = Blueprint('main', __name__)


def get_turtle_data():
    """
    TurtleScheduler 역할: DailyScheduler를 사용해 조건검색(터틀) 신호를 수집하고,
    시스템별 종목 리스트와 마지막 업데이트 시간을 반환합니다.
    """
    scheduler = DailyScheduler()
    # fetch_turtle_signals는 내부적으로 run_condition_collection을 호출합니다.
    results = scheduler.fetch_turtle_signals()

    # 시스템 1, 시스템 2 구분
    system1 = results.get('1', [])
    system2 = results.get('2', [])

    # 마지막 업데이트 시각
    last_updated = datetime.now()

    return {
        'system1': system1,
        'system2': system2,
        'last_updated': last_updated
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
