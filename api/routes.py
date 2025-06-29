# API 라우트 정의
from flask import Blueprint

api_bp = Blueprint('api', __name__)

@api_bp.route('/hello')
def hello():
    return {'message': 'Hello, API!'}
