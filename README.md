# 붕어빵 판매 관리 시스템 🐟

Django 기반의 붕어빵 판매 관리 웹 애플리케이션입니다.

## 주요 기능

- **판매 관리 캘린더**: 날짜별로 판매 데이터를 관리하고 조회
- **판매 조절**: +1/+3/-1/-3 버튼으로 빠른 판매 수량 입력
- **대시보드**: 시간대별 판매 분포, 품목별 통계, 재료 소모량 분석
- **품목 관리**: 판매 품목, 재료, 레시피 설정
- **타이머**: 붕어빵 굽기 시간 관리
- **사용자 인증**: 로그인/회원가입 기능

## 기술 스택

- **Backend**: Django 5.2.9
- **Database**: SQLite3
- **Frontend**: HTML, CSS, JavaScript
- **Charts**: Chart.js 3.9.1
- **Timezone**: pytz (Asia/Seoul)

## 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/BungeoSales.git
cd BungeoSales
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 필요한 값을 수정하세요:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

`.env` 파일에서 SECRET_KEY를 새로 생성하세요:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. 데이터베이스 마이그레이션

```bash
python manage.py migrate
```

### 6. 슈퍼유저 생성 (선택사항)

```bash
python manage.py createsuperuser
```

### 7. 서버 실행

```bash
python manage.py runserver
```

브라우저에서 `http://127.0.0.1:8000/` 접속

## 사용 방법

1. **회원가입/로그인**: 첫 방문 시 회원가입 후 로그인
2. **품목 설정**: 상단 메뉴 → 설정 → 품목 추가 (예: 팥붕어빵, 슈크림붕어빵)
3. **재료 설정**: 재료 이름과 그램당 가격 입력
4. **레시피 설정**: 각 품목별로 필요한 재료와 사용량 설정
5. **판매 관리**: 캘린더에서 날짜 클릭 → +1/+3 버튼으로 판매 기록
6. **대시보드**: 판매 분석 및 통계 확인

## 프로젝트 구조

```
BungeoSales/
├── config/              # Django 설정
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── sales/               # 메인 앱
│   ├── models.py        # 데이터 모델
│   ├── views.py         # 뷰 로직
│   ├── urls.py          # URL 라우팅
│   └── templates/       # HTML 템플릿
├── .env                 # 환경 변수 (git에 포함 안됨)
├── .env.example         # 환경 변수 예시
├── .gitignore           # Git 무시 파일
├── requirements.txt     # 패키지 의존성
├── manage.py            # Django 관리 스크립트
└── README.md            # 프로젝트 문서
```

## 주요 모델

- **Item**: 판매 품목 (붕어빵 종류)
- **Ingredient**: 재료
- **RecipeComponent**: 레시피 구성
- **SalesDay**: 일별 판매 데이터
- **SalesCount**: 품목별 판매 수량
- **SalesEvent**: 판매 이벤트 로그 (시간대별 분석용)
- **TimerLog**: 타이머 기록

## 특징

### UNDO 방식의 취소 기능
- 버튼을 누르는 순간의 시간이 기록되므로, "- 버튼"으로 취소 시 가장 최근 이벤트부터 되돌립니다
- 이를 통해 시간대 분석의 정확도를 높입니다

### 실시간 업데이트
- AJAX를 사용하여 페이지 리로드 없이 숫자만 즉시 갱신
- 태블릿/모바일에서도 빠른 조작 가능

### 차트 시각화
- Chart.js를 사용한 직관적인 데이터 시각화
- 품목 점유율 (도넛 차트)
- 시간대별 판매 분포 (막대/라인 차트)

### 세션 보안
- 브라우저 종료 시 자동 로그아웃
- 서버 재시작 시 세션 초기화 (메모리 기반 캐시)



