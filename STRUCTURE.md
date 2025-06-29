my_flask_app/
├── app.py                 # 메인 애플리케이션 파일
├── config.py             # 설정 파일
├── requirements.txt      # 의존성 패키지 목록
├── .env                  # 환경 변수 (git에 포함하지 않음)
├── .gitignore           # Git 무시 파일 목록
│
├── api/                 # API 관련 파일들
│   ├── __init__.py
│   ├── routes.py        # API 라우트 정의
│   ├── models.py        # 데이터 모델
│   └── utils.py         # 유틸리티 함수들
│
├── templates/           # HTML 템플릿 파일들
│   ├── base.html        # 기본 레이아웃
│   ├── index.html       # 메인 페이지
│   └── components/      # 재사용 가능한 컴포넌트들
│       └── navbar.html
│
├── static/              # 정적 파일들
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── images/
│       └── logo.png
│
├── services/            # 비즈니스 로직 서비스들
│   ├── __init__.py
│   ├── auth_service.py  # 인증 관련 서비스
│   └── data_service.py  # 데이터 처리 서비스
│
└── tests/               # 테스트 파일들
    ├── __init__.py
    ├── test_api.py
    └── test_services.py