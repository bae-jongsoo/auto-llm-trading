# PROJECT_RULES

## 프로젝트 개요
- 문서 기준: 자동 LLM 트레이딩 운영 시스템 PRD v3.0 (작성일 2026-03-06)
- 목적: 개발 착수 전 기준 문서로 기능 범위, 운영 정책, 성공 기준을 고정한다.
- 프로젝트 배경:
  - LLM을 활용해 국내 주식 단기 매매 자동화를 검증한다.
  - 초기 단계는 실거래 대신 DB 기반 가상 주문/체결 이력으로 자산 증감을 검증한다.
  - LLM 판단 과정/결과는 추적 가능해야 한다.
- 제품 목표:
  1. 관심 종목군의 핵심 데이터(시장/뉴스/공시/수급)를 정기 수집한다.
  2. 계좌 상태 기반 실행 단위 행동(BUY/HOLD 또는 SELL/HOLD)을 산출한다.
  3. 판단 근거와 실행 결과를 감사 가능한 형태로 저장한다.
  4. 종목은 사전 지정하며, 필요 시 장기 추세를 판단 근거로 활용한다.
- 대상 종목(수집/트레이딩 대상 10개로 제한):

| Stock Code | DART Corp Code | Name |
| --- | --- | --- |
| 005930 | 00126380 | 삼성전자 |
| 000660 | 00164779 | SK하이닉스 |
| 105560 | 00688996 | KB금융 |
| 055550 | 00382199 | 신한지주 |
| 035420 | 00266961 | 네이버 |
| 035720 | 00258801 | 카카오 |
| 000720 | 00164478 | 현대건설 |
| 005380 | 00164742 | 현대차 |
| 000270 | 00106641 | 기아 |
| 034020 | 00159616 | 두산에너빌리티 |

- 트레이딩 루프 기준:
```python
while True:
    if has_position():
        sell_prompt = build_sell_prompt(stock=position_stock)
        decision = ask_llm(sell_prompt)
        if decision["decision"]["result"] == "SELL":
            simulate_sell()
    else:
        buy_prompt = build_buy_prompt(stocks=["005930", "000660", "..."])
        decision = ask_llm(buy_prompt)
        if decision["decision"]["result"] == "BUY":
            simulate_buy()
```
- 운영 정책:
  - 종목은 사전 지정한다.
  - 초기 단계에서는 실거래를 수행하지 않고 DB 기반 가상 잔고를 사용한다.
  - 동시 보유는 1종목으로 제한한다.
  - 수집 데이터는 DB에 저장한다.
  - 웹소켓 데이터는 Redis에 최신 1시간만 저장하고, 그 이전 데이터는 폐기한다.
  - 현재 단계에서는 슬리피지/수수료/부분체결을 고려하지 않는다.
  - 가상 주문은 요청값 기준 즉시 체결(주문 필드 = 결과 필드)로 처리한다.
  - 각 프로세스는 Django management command 형태의 1회성 수집 커맨드를 제공한다.
  - 모든 시간 기준은 KST 고정(`TIME_ZONE = "Asia/Seoul"`), 휴장일 제외/월~금 스케줄만 적용한다.

## 기술 스택
- 언어/런타임: Python 3.12+
- 웹 프레임워크: Django (`pyproject.toml`: `django>=5.1`)
- API: Django Ninja (`django-ninja>=1.0`)  
  참고 구현: `apps/todos/api.py`, `apps/todos/schemas.py`
- DB: PostgreSQL (`django.db.backends.postgresql`, `psycopg2-binary>=2.9`)
- 캐시/실시간 저장소: Redis (`django-redis>=5.4`)
- HTTP 클라이언트: `requests>=2.31`
- 환경변수 로드: `python-dotenv>=1.0` (`config/settings.py`에서 `load_dotenv()`)
- 테스트: `pytest>=8.0`, `pytest-django>=4.8`, `DJANGO_SETTINGS_MODULE=config.settings_test`

## 디렉토리 구조
- `apps/`
  - `apps/todos/`
    - `api.py`: Django Ninja Router
    - `schemas.py`: 입출력 스키마
    - `services.py`: 비즈니스 로직
    - `models.py`: ORM 모델
    - `management/commands/todo_list.py`: management command 예시
  - `apps/news/models.py`
  - `apps/dart/models.py`
  - `apps/market/models.py`
  - `apps/trader/models.py`
  - `apps/asset/models.py`
  - `apps/ws/`
- `shared/`
  - `shared/external/telegram.py`: 외부 API 연동 모듈
  - `shared/models.py`: 공통 모델 믹스인/수집 베이스
  - `shared/stock_universe.py`: 대상 종목 코드/이름 관리
- `config/`
  - `config/settings.py`, `config/settings_test.py`
  - `config/urls.py`
- `tests/`
  - `tests/test_todos.py`

## 코딩 규칙
- 레이어 구조(필수):
  - `API / Command -> services.py(비즈니스 로직) -> Model/DB`
  - API/Command는 입력 파싱과 호출 위주로 얇게 유지한다.
  - 비즈니스 규칙, 검증, 상태 전이, 예외는 `services.py`에 둔다.
- 테스트 구조(필수):
  - 테스트는 `services.py` 함수를 직접 호출해 검증한다.
  - API 응답 포맷, Command stdout 문자열에 의존하는 테스트를 작성하지 않는다.
- `shared/` 규칙(필수):
  - `shared/external/`: 외부 API 연동 모듈(텔레그램, 네이버 뉴스 등), mock 대상 함수 배치
  - `shared/utils/`: 여러 앱 공통 유틸리티(날짜/타입 변환 등) 배치
  - 앱 내부에 중복 유틸리티를 만들지 않는다.
- 종목 정책:
  - 지원 종목 코드는 `shared/stock_universe.py`의 `TARGET_STOCKS`를 기준으로 강제한다.
  - 사전 지정 10개 종목 외 코드는 허용하지 않는다.
- 시간 정책:
  - KST(`Asia/Seoul`) 고정.
  - 스케줄은 월~금 기준으로 운영한다.

## DB 규칙
- 공통 규칙:
  - 모든 테이블에는 조회 성능을 위한 적절한 인덱스를 구성한다.
  - 수집 테이블은 `external_id`를 관리한다.
  - 수집 커맨드는 `external_id` 기준 upsert(또는 동등한 중복 방지 방식)로 idempotent하게 동작한다.

- 현재 코드 기준 핵심 모델:
  - `apps/news/models.py::News`
    - 공통: `stock_code`, `external_id(unique)`, `published_at`, `created_at`
    - 필드: `link`, `title`, `summary`, `useful`, `description`
  - `apps/dart/models.py::DartDisclosure`
    - 공통: `stock_code`, `external_id(unique)`, `published_at`, `created_at`
    - 필드: `corp_code`, `rcept_no`, `title`, `link`, `description`
  - `apps/market/models.py::MarketSnapshot`
    - 공통: `stock_code`, `external_id(unique)`, `published_at`, `created_at`
    - 전체 수집 필드를 모두 저장한다.
  - `apps/trader/models.py::DecisionHistory`
    - `request_payload`, `response_payload`, `parsed_decision`, `processing_time_ms`, `is_error`, `error_message`, `result`, `created_at`
  - `apps/trader/models.py::OrderHistory`
    - `decision_history(FK)`, `stock_code`, `order_price`, `order_quantity`, `order_total_amount`, `result_price`, `result_quantity`, `result_total_amount`, `order_placed_at`, `result_executed_at`, `created_at`
  - `apps/asset/models.py::Asset`
    - `stock_code(NULL이면 현금 row)`, `quantity`, `unit_price`, `total_amount`, `created_at`, `updated_at`

- 8.1 수집용 테이블 요구사항:
  - 네이버 뉴스
    - API: `https://openapi.naver.com/v1/search/news.json`
    - 뉴스 API 본문 미제공이므로 본문 요약 필드 추가 저장
    - 처리 흐름:
      1. API 응답 수신 후 DB 저장
      2. `link` 필드로 원문 조회 후 본문 텍스트 추출
      3. `ask_llm(...)`으로 원문 요약 + 단타 유용성 판단
      4. 응답 형식: `{"summary": "...", "useful": true}`
      5. `summary`, `useful` 필드 업데이트
    - 크롤링 실패 처리:
      - 성공 시: LLM 요약 결과를 `summary`에 저장
      - 실패 시: 네이버 API의 `description`을 `summary`에 저장, `useful`은 `null`
  - 다트 공시
    - OpenDartReader `list` 호출
  - 종목 현재 정보
    - API: `https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price`
    - 실시간 체결/호가로 커버되지 않는 종목 기초 데이터 저장
    - 전체 수집 필드(전부 DB 저장):

```
per, pbr, eps, bps, stac_month, lstn_stcn, hts_avls, cpfn, stck_fcam,
w52_hgpr, w52_hgpr_date, w52_hgpr_vrss_prpr_ctrt,
w52_lwpr, w52_lwpr_date, w52_lwpr_vrss_prpr_ctrt,
d250_hgpr, d250_hgpr_date, d250_hgpr_vrss_prpr_rate,
d250_lwpr, d250_lwpr_date, d250_lwpr_vrss_prpr_rate,
stck_dryy_hgpr, dryy_hgpr_date, dryy_hgpr_vrss_prpr_rate,
stck_dryy_lwpr, dryy_lwpr_date, dryy_lwpr_vrss_prpr_rate,
hts_frgn_ehrt, frgn_hldn_qty, frgn_ntby_qty, pgtr_ntby_qty,
vol_tnrt, whol_loan_rmnd_rate, marg_rate,
crdt_able_yn, ssts_yn, iscd_stat_cls_code, mrkt_warn_cls_code,
invt_caful_yn, short_over_yn, sltr_yn, mang_issu_cls_code,
temp_stop_yn, oprc_rang_cont_yn, clpr_rang_cont_yn,
grmn_rate_cls_code, new_hgpr_lwpr_cls_code,
rprs_mrkt_kor_name, bstp_kor_isnm,
vi_cls_code, ovtm_vi_cls_code,
last_ssts_cntg_qty, apprch_rate
```

    - 프롬프트 포함 필드(15개):

| 카테고리 | 필드 | 설명 |
| --- | --- | --- |
| 밸류에이션 | per | PER |
|  | pbr | PBR |
|  | eps | EPS |
|  | hts_avls | 시가총액 |
| 수급 | hts_frgn_ehrt | 외국인 소진율 |
|  | frgn_ntby_qty | 외국인 순매수 수량 |
|  | pgtr_ntby_qty | 프로그램 순매수 수량 |
|  | vol_tnrt | 거래량 회전율 |
| 가격 범위 | w52_hgpr | 52주 최고가 |
|  | w52_lwpr | 52주 최저가 |
|  | w52_hgpr_vrss_prpr_ctrt | 52주 최고가 대비 현재가 비율 |
|  | w52_lwpr_vrss_prpr_ctrt | 52주 최저가 대비 현재가 비율 |
| 리스크 | mrkt_warn_cls_code | 시장경고 코드 |
|  | invt_caful_yn | 투자유의 여부 |
|  | short_over_yn | 단기과열 여부 |

- 8.2 주문 이력 테이블 요구사항:
  - LLM 판단 이력:
    - 요청 프롬프트 원문, 응답 원문 저장
    - 파싱된 결정(JSON), 처리 시간(ms), 에러 여부 저장
  - LLM 주문 이력:
    - HOLD가 아닌 경우 주문 실행 후 이력 저장
    - 주문 종목/가격/수량, 주문 결과, 판단 이력 FK 저장
    - 가상 주문 단계: 주문 필드 = 결과 필드(즉시 체결)
    - 실거래 연동 단계: 주문 후 체결 응답으로 결과 필드 업데이트

- 8.3 자산 테이블 요구사항:
  - 현재 보유 주식: 종목코드, 수량, 주당 금액, 총금액 등
  - 현금: 종목코드 `null`, 수량 `1`, 주당금액 = 총금액 = 현재 남은 현금

## API 규칙
- 범위:
  - 트레이딩 도메인 초기 범위에서 API는 제공하지 않는다(관리/조회 API는 추후 결정).
  - 참고 구현(`apps/todos/api.py`)처럼 Router는 서비스 함수 호출에 집중한다.
- 외부 수집 API:
  - 네이버 뉴스: `https://openapi.naver.com/v1/search/news.json`
  - 한국투자증권 종목 현재 정보: `https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price`
  - 다트 공시: OpenDartReader `list`
- LLM 요청 공통 함수:
```python
def ask_llm(
    prompt: str,
    timeout_seconds: int = 25,
) -> str:
    nanobot_bin = os.getenv("NANOBOT_BIN", "nanobot")
    result = subprocess.run(
        [nanobot_bin, "agent", "--no-markdown", "-m", prompt],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
```
- LLM 실패 처리:
  - JSON 파싱 실패, 타임아웃, 빈 응답 등 비정상 케이스는 기본 HOLD 처리
  - 실패 내역은 판단 이력 테이블에 에러 여부/원문 응답과 함께 저장
- 프롬프트 규격:
  - 뉴스 요약
```
아래는 뉴스 본문이다. 이걸 요약하고 주식 단타에 도움이 되는지 판단 후,
{"summary": "...", "useful": true} 형태로 응답 해달라.

<뉴스 본문>
...
```
  - 매수 판단
    - 자산 테이블 기준으로 보유 종목이 없을 때 실행한다.
    - 매수 프롬프트는 사전 지정된 10개 종목의 수집 정보를 모아 생성한다.
    - 프롬프트 포함 데이터:
      - 10개 종목별 정보
      - Redis 체결/호가 기반 최근 10분 가격 흐름
      - 자산 테이블 잔액
      - 종목 현재 정보 최신 row (프롬프트 포함 필드 15개)
      - 최근 7일 다트 공시
      - 최근 10건 뉴스 (`useful=true` 또는 `useful is null`인 것만)
      - 각 데이터의 수집 시간을 포함하여 LLM이 시간 경과를 판단할 수 있도록 한다.
```
현재 시각은 {current_time}입니다.
현재 우리는 N원의 자산을 가지고 있습니다.
아래 <주식 정보>는 단타(익절) 관점에서 10개 종목 중 매수 후보를 판단하기 위한 근거입니다.
각 데이터에는 수집 시각이 포함되어 있으니, 현재 시각과의 차이를 감안하여 판단하세요.
근거를 바탕으로 매수 가능 종목이 있으면 BUY 신호와 점수를, 없으면 HOLD와 0점을 부여하세요.
또한 현재 잔액 기준으로 점수가 가장 높은 1개 종목의 매수 수량/가격을 제안하세요.
응답은 아래 JSON 형태여야 합니다.
{
  "decision": {
    "result": "BUY",  # 또는 HOLD
    "종목코드": "...",
    "수량": 0,
    "가격": 0
  },
  "reasons": [
    {"종목코드": "...", "종목명": "...", "decision": "BUY", "point": 80, "reason": "..."},
    {"종목코드": "...", "종목명": "...", "decision": "HOLD", "point": 0, "reason": "..."}
  ]
}

<주식정보>
[
  {
    "종목코드": "...",
    "종목명": "...",
    "뉴스": [...],
    "공시": [...],
    "시간별체결가정보": [...],
    "시간별호가정보": [...],
    "주식기본정보": { ... }
  }
]
```
  - 매도 판단
    - 보유 종목이 있을 때 실행한다.
    - 매도 프롬프트는 현재 보유 중인 1개 종목의 수집 정보를 모아 생성한다.
    - 요청/응답 형식은 매수 판단과 동일하되, 1개 종목 정보만 전달한다.
    - 매수/매도 프롬프트에 "가급적 단타(익절 중심)" 원칙 포함

## 테스트 전략
- 기준 파일: `tests/test_todos.py`
- 완료 조건:
  - `tests/` 폴더의 테스트가 Ralph 루프 완료 조건이다.
- 작성 원칙:
  - 서비스 함수를 직접 호출하여 검증한다(`apps.<domain>.services` 직접 호출).
  - 내부 서비스 로직은 mock하지 않는다.
  - 외부 경계(`shared/external/`)만 mock/patch 한다.
  - 예외는 `pytest.raises(..., match=...)` 형태로 검증한다.
  - `@pytest.mark.django_db`를 사용해 DB 상호작용을 명시한다.
  - API 응답 JSON 포맷, management command stdout 포맷에 의존하는 테스트를 작성하지 않는다.

## 금지 사항
- API/Command 레이어에 비즈니스 로직을 직접 구현하는 행위
- 앱 내부에 공통 유틸리티를 중복 구현하는 행위(`shared/utils` 사용)
- 외부 API 직접 호출 코드를 서비스 로직에 산재시키는 행위(`shared/external` 경유)
- 사전 지정 10개 종목 외 데이터를 수집/트레이딩 대상으로 확장하는 행위(범위 변경 승인 전)
- LLM 실패 시 BUY/SELL를 강행하는 행위(HOLD 기본 처리 위반)
- 현재 단계에서 슬리피지/수수료/부분체결을 임의 반영하는 행위
- 테스트에서 stdout/API 포맷에 의존하거나, 내부 서비스를 과도하게 mock하는 행위

## 환경변수
- 루트 `.env`에서 관리하고 `config/settings.py`에서 로드한다.
- PRD 필수 환경변수:
```env
KIS_APP_KEY=
KIS_APP_SECRET=
KIS_HTS_ID=
KIS_ACCT_STOCK=
KIS_PROD_TYPE=01

DART_API_KEY=

DB_USER=alt
DB_PASSWORD=alt
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=alt

REDIS_URL=redis://127.0.0.1:6379/0

NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
```
- 현재 코드에서 추가 사용 환경변수:
  - `SECRET_KEY`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `NANOBOT_BIN` (`ask_llm` 기본값: `nanobot`)

## 기타
- 스케줄 정책:

| 대상 | 주기 | 비고 |
| --- | --- | --- |
| 뉴스 | 매 5분 (0,5,10,15...분) | |
| 다트 | 매 10분 (0,10,20...분) | |
| 장중 시세 정보 | 월~금 09:00~15:30, 매 1분 | |
| 트레이딩(with LLM) | 월~금 09:10~15:30, 1회성 커맨드 반복 | 웹소켓 데이터 10분 축적 후 시작, systemd Restart=always로 연속 실행 |

- systemd/운영 명령 요구사항:
  - 필수 타겟: `systemd-install`, `systemd-remove`, `systemd-restart`, `systemd-status`, `systemd-timers`, `systemd-overview`, `check`
  - systemd 실행 커맨드는 에러 방지를 위해 반드시 절대 경로 사용
  - 모니터링 명령:
    - `systemctl list-timers`
    - `systemctl status alt-<name>`
    - `systemctl status alt-<name>.timer`
    - `journalctl -u alt-<name>.service -n 200 --no-pager`
    - `journalctl -u alt-<name>.service -f`
  - 대상 서비스(타이머): `alt-news`, `alt-dart`, `alt-market-realtime`
  - 대상 서비스(상주): `alt-ws-subscribe`, `alt-trader`

- 도메인 앱 역할:

| 앱 | 역할 |
| --- | --- |
| news | 뉴스 수집 |
| dart | 공시 수집 |
| market | 시세/종목 정보 수집 |
| trader | 매수/매도 판단 및 주문 |
| ws | 웹소켓 구독 |
| asset | 자산(잔고/보유주식) 관리 |

- 공통 모듈 정책:
  - `ask_llm` 등 LLM 관련 공통 로직은 `shared/` 구조에서 관리한다.
