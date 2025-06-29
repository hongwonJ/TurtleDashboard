import logging
import threading
import schedule
import time
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from typing import Dict, List

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        
        stock_data = {
            'code': stock_code,
            'name': f'종목{stock_code}',
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
        
        stock_data = {
            'code': stock_code,
            'name': f'종목{stock_code}',
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

def start_scheduler():
    """스케줄러 시작"""
    # 매일 오후 4시에 실행
    schedule.every().day.at("16:00").do(mock_turtle_scheduler)
    
    # 테스트용: 매 5분마다 실행 (개발 중에만)
    # schedule.every(5).minutes.do(mock_turtle_scheduler)
    
    logger.info("터틀 스케줄러 등록 완료 - 매일 오후 4시 실행")
    
    while True:
        schedule.run_pending()
        time.sleep(30)  # 30초마다 체크

def create_app():
    app = Flask(__name__)
    logger.info("터틀 대시보드 앱 생성 중...")
    
    @app.route('/')
    def index():
        """메인 페이지"""
        logger.info("메인 페이지 요청")
        
        # 현재 데이터 가져오기
        system1 = turtle_data_store.get('system1', [])
        system2 = turtle_data_store.get('system2', [])
        last_updated = turtle_data_store.get('last_updated')
        status = turtle_data_store.get('status', 'waiting')
        
        # HTML 템플릿
        template = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>🐢 터틀 대시보드</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                h1 { color: #2c3e50; text-align: center; }
                .status { text-align: center; margin: 20px 0; padding: 10px; 
                         background: #ecf0f1; border-radius: 5px; }
                .system { margin: 20px 0; padding: 15px; background: white; 
                         border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .system h2 { margin-top: 0; }
                .system1 h2 { color: #3498db; }
                .system2 h2 { color: #e74c3c; }
                table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background: #f8f9fa; font-weight: bold; }
                .price { text-align: right; font-family: monospace; }
                .stop-loss { color: #e74c3c; font-weight: bold; }
                .trailing-stop { color: #9b59b6; font-weight: bold; }
                .add-position { color: #f39c12; font-weight: bold; }
                .entry-price { color: #6f42c1; font-weight: bold; }
                .no-data { text-align: center; color: #7f8c8d; padding: 30px; }
                .refresh-btn { background: #3498db; color: white; border: none; 
                              padding: 10px 20px; border-radius: 5px; cursor: pointer;
                              margin: 10px 5px; }
                .api-links { text-align: center; margin: 20px 0; }
                .api-links a { margin: 0 10px; color: #3498db; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🐢 터틀 트레이딩 대시보드</h1>
                
                <div class="status">
                    <strong>상태:</strong> {{ status }}
                    {% if last_updated %}
                    | <strong>마지막 업데이트:</strong> {{ last_updated.strftime('%Y-%m-%d %H:%M:%S') }}
                    {% endif %}
                    <br>
                    <button class="refresh-btn" onclick="window.location.reload()">새로고침</button>
                    <button class="refresh-btn" onclick="manualUpdate()">수동 업데이트</button>
                </div>
                
                <div class="api-links">
                    <a href="/api/turtle-data">API 데이터</a> |
                    <a href="/api/health">헬스 체크</a> |
                    <a href="/api/manual-update">수동 업데이트</a>
                </div>
                
                <!-- System 1 -->
                <div class="system">
                    <h2>터틀 System 1 (단기) - {{ system1|length }}개 종목</h2>
                    {% if system1 %}
                    <table>
                        <thead>
                            <tr>
                                <th>종목코드</th><th>종목명</th><th>진입일</th><th>진입가</th>
                                <th>현재가</th><th>손절가</th><th>트레일링</th><th>추가매수</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for stock in system1 %}
                            <tr>
                                <td>{{ stock.code }}</td>
                                <td>{{ stock.name }}</td>
                                <td>{{ stock.entry_date }}</td>
                                <td class="price entry-price">{{ "{:,}".format(stock.entry_price|int) }}</td>
                                <td class="price">{{ "{:,}".format(stock.current|int) }}</td>
                                <td class="price stop-loss">{{ "{:,}".format(stock.stop_loss|int) }}</td>
                                <td class="price trailing-stop">{{ "{:,}".format(stock.trailing_stop|int) }}</td>
                                <td class="price add-position">{{ "{:,}".format(stock.add_position|int) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <div class="no-data">아직 신호가 없습니다.</div>
                    {% endif %}
                </div>
                
                <!-- System 2 -->
                <div class="system">
                    <h2>터틀 System 2 (장기) - {{ system2|length }}개 종목</h2>
                    {% if system2 %}
                    <table>
                        <thead>
                            <tr>
                                <th>종목코드</th><th>종목명</th><th>진입일</th><th>진입가</th>
                                <th>현재가</th><th>손절가</th><th>트레일링</th><th>추가매수</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for stock in system2 %}
                            <tr>
                                <td>{{ stock.code }}</td>
                                <td>{{ stock.name }}</td>
                                <td>{{ stock.entry_date }}</td>
                                <td class="price entry-price">{{ "{:,}".format(stock.entry_price|int) }}</td>
                                <td class="price">{{ "{:,}".format(stock.current|int) }}</td>
                                <td class="price stop-loss">{{ "{:,}".format(stock.stop_loss|int) }}</td>
                                <td class="price trailing-stop">{{ "{:,}".format(stock.trailing_stop|int) }}</td>
                                <td class="price add-position">{{ "{:,}".format(stock.add_position|int) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <div class="no-data">아직 신호가 없습니다.</div>
                    {% endif %}
                </div>
            </div>
            
            <script>
                function manualUpdate() {
                    fetch('/api/manual-update', {method: 'POST'})
                        .then(response => response.json())
                        .then(data => {
                            alert(data.message);
                            window.location.reload();
                        })
                        .catch(error => {
                            alert('업데이트 실패: ' + error);
                        });
                }
                
                // 5분마다 자동 새로고침
                setInterval(() => {
                    window.location.reload();
                }, 5 * 60 * 1000);
            </script>
        </body>
        </html>
        '''
        
        return render_template_string(template, 
                                    system1=system1, 
                                    system2=system2,
                                    last_updated=last_updated,
                                    status=status)
    
    @app.route('/api/health')
    def health():
        """헬스 체크"""
        return jsonify({
            'status': 'ok',
            'message': '터틀 대시보드 정상 작동',
            'data_status': turtle_data_store.get('status', 'waiting'),
            'last_updated': turtle_data_store.get('last_updated').isoformat() if turtle_data_store.get('last_updated') else None
        })
    
    @app.route('/api/turtle-data')
    def turtle_data():
        """터틀 데이터 API"""
        return jsonify({
            'system1': turtle_data_store.get('system1', []),
            'system2': turtle_data_store.get('system2', []),
            'last_updated': turtle_data_store.get('last_updated').isoformat() if turtle_data_store.get('last_updated') else None,
            'status': turtle_data_store.get('status', 'waiting')
        })
    
    @app.route('/api/manual-update', methods=['POST'])
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
    
    logger.info("터틀 대시보드 앱 설정 완료")
    return app

# gunicorn이 찾을 수 있도록 모듈 레벨에 app 노출
app = create_app()

# 스케줄러 시작 (백그라운드 스레드)
try:
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info('터틀 스케줄러 스레드 시작 완료')
except Exception as e:
    logger.error(f'스케줄러 시작 실패: {e}')

logger.info('🐢 터틀 대시보드 앱 시작 완료')

if __name__ == '__main__':
    logger.info('개발 모드로 Flask 앱 실행')
    app.run(debug=True, host='0.0.0.0', port=8000)
