from flask import Flask, render_template
from flask_caching import Cache
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from services.kiwoom_service import KiwoomAPIService

app = Flask(__name__)
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)
cache.init_app(app)
cache.set('turtle_list', [])
cache.set('new_turtle_list', [])
service = KiwoomAPIService()

def fetch_and_update_turtle_list():
    today = datetime.now().strftime('%Y-%m-%d')
    today_list = service.get_daily_turtle_list()
    existing = cache.get('turtle_list') or []
    new_items = [t for t in today_list if t not in existing]
    cache.set('new_turtle_list', new_items)
    cache.set('turtle_list', today_list)
    print(f"[{today} 16:00] New Turtle: {new_items}")

scheduler = BackgroundScheduler(timezone='Asia/Seoul')
scheduler.add_job(fetch_and_update_turtle_list, 'cron', hour=16, minute=0, id='turtle_fetch')
scheduler.start()

@app.route('/')
def index():
    all_turtles = cache.get('turtle_list') or []
    new_turtles = cache.get('new_turtle_list') or []
    stocks_all = [{'ticker': t, 'name': '', 'signal': ''} for t in all_turtles]
    stocks_new = [{'ticker': t, 'name': '', 'signal': '신규 추가'} for t in new_turtles]
    return render_template('index.html', stocks_all=stocks_all, stocks_new=stocks_new)

if __name__ == '__main__':
    app.run(debug=True)