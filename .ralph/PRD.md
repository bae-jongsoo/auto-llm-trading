# 제품 요구사항 문서(PRD)

- 문서명: 자동 LLM 트레이딩 운영 시스템 PRD
- 버전: v3.0
- 작성일: 2026-03-06
- 문서 목적: 개발 착수 전 기준 문서로서 기능 범위, 운영 정책, 성공 기준을 정의한다.

## 1. 프로젝트 배경

본 프로젝트는 LLM을 활용해 국내 주식 단기 매매 자동화를 검증하기 위한 시도다.
국내 주식을 선택한 이유는 세금 측면의 이점과 한국투자증권 API의 활용성 때문이다.

LLM이 매수/매도를 판단할 수 있도록 필요한 정보를 사전에 수집해 DB에 저장하고,
주기적으로 DB를 조회해 컨텍스트를 조립한 뒤 LLM이 의사결정을 수행한다.

## 2. 구현 목표

- 아이디어의 수익성을 우선 검증한다.
- 초기 단계에서는 실거래 대신 DB 기반 가상 주문/체결 이력을 기록해 자산 증감을 확인한다.
- LLM의 판단 과정과 결과를 추적 가능해야 한다.

## 3. 제품 목표

1. 관심 종목군의 핵심 데이터(시장/뉴스/공시/수급)를 정기 수집한다.
2. 계좌 상태를 기반으로 실행 단위 행동(BUY/HOLD 또는 SELL/HOLD)을 산출한다.
3. 판단 근거와 실행 결과를 감사 가능한 형태로 저장한다.
4. 종목은 사전 지정하며, 필요한 경우 장기 추세도 판단 근거로 활용한다.

## 4. 대상 종목

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

수집 및 트레이딩 대상은 위 10개 종목으로 제한한다.

## 5. 기능 요구사항

### 5.1 정보 수집

수집 대상 상세는 8장(데이터베이스 요구사항)에 정의한다.

### 5.2 트레이딩

- 수집된 정보를 조합해 컨텍스트를 생성하고, 이를 기반으로 LLM에 질의한다.
- 매수 프롬프트는 사전 지정된 10개 종목의 수집 정보를 모아 생성한다.
- 매도 프롬프트는 현재 보유 중인 1개 종목의 수집 정보를 모아 생성한다.
- 동시 보유는 1종목으로 제한한다.
- 가상 주문 단계에서는 주문 즉시 체결로 처리한다. (주문 필드 = 결과 필드)
- 실거래 연동 시에는 주문 후 체결 응답을 받아 결과 필드를 업데이트한다.

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

## 6. 구현 및 운영 정책

- 종목은 사전에 지정한다.
- 초기 단계에서는 실거래를 수행하지 않고, DB 기반 가상 잔고를 사용한다.
- 수집 데이터는 DB에 저장한다.
- 웹소켓 데이터는 Redis에 최신 1시간만 저장하고, 그 이전 데이터는 폐기한다.
- 현재 단계에서는 슬리피지/수수료/부분체결을 고려하지 않는다. (가상 주문은 요청값 기준 즉시 체결)
- 각 프로세스는 Django management command 형태의 1회성 수집 커맨드를 제공한다.
- Makefile을 통해 systemd 설치/삭제를 수행한다.
- systemd 실행 커맨드는 에러 방지를 위해 반드시 절대 경로를 사용한다.

스케줄:

| 대상 | 주기 | 비고 |
| --- | --- | --- |
| 뉴스 | 매 5분 (0,5,10,15...분) | |
| 다트 | 매 10분 (0,10,20...분) | |
| 장중 시세 정보 | 월~금 09:00~15:30, 매 1분 | |
| 트레이딩(with LLM) | 월~금 09:10~15:30, 1회성 커맨드 반복 | 웹소켓 데이터 10분 축적 후 시작, systemd Restart=always로 연속 실행 |

## 7. 필요 환경변수

루트 `.env`에서 관리하며 `settings.py`에서 로드한다.

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

## 8. 데이터베이스 요구사항

> 모든 테이블에는 조회 성능을 위한 적절한 인덱스를 구성해야 한다.
> 수집 테이블은 중복 체크를 위해 `external_id`를 관리해야 한다.
> 수집 커맨드는 `external_id` 기준 upsert(또는 동등한 중복 방지 방식)로 idempotent하게 동작해야 한다.

### 8.1 수집용 테이블

#### 네이버 뉴스

- API: https://openapi.naver.com/v1/search/news.json
- 뉴스 API는 본문을 제공하지 않으므로 본문 요약 필드를 추가 저장해야 한다.
- 처리 흐름:
  1. API 응답 수신 후 DB 저장
  2. `link` 필드로 원문 조회 후 본문 텍스트 추출
  3. `ask_llm(...)`으로 원문 요약 + 단타 유용성 판단
  4. 응답 형식: `{"summary": "...", "useful": true}`
  5. `summary`, `useful` 필드 업데이트
- 크롤링 실패 처리:
  - 크롤링 성공 시: LLM 요약 결과를 summary에 저장
  - 크롤링 실패 시: 네이버 API의 description을 summary에 저장, useful은 null

#### 다트 공시

- OpenDartReader `list` 호출

#### 종목 현재 정보

- API: https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price
- 실시간 체결/호가만으로 커버되지 않는 종목 기초 데이터 저장
- 전체 수집 필드는 아래 목록 참조 (DB에는 전부 저장하되, 프롬프트에는 선별 필드만 포함)

**전체 수집 필드:**

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

**프롬프트 포함 필드 (15개):**

| 카테고리 | 필드 | 설명 |
| --- | --- | --- |
| 밸류에이션 | per | PER |
| | pbr | PBR |
| | eps | EPS |
| | hts_avls | 시가총액 |
| 수급 | hts_frgn_ehrt | 외국인 소진율 |
| | frgn_ntby_qty | 외국인 순매수 수량 |
| | pgtr_ntby_qty | 프로그램 순매수 수량 |
| | vol_tnrt | 거래량 회전율 |
| 가격 범위 | w52_hgpr | 52주 최고가 |
| | w52_lwpr | 52주 최저가 |
| | w52_hgpr_vrss_prpr_ctrt | 52주 최고가 대비 현재가 비율 |
| | w52_lwpr_vrss_prpr_ctrt | 52주 최저가 대비 현재가 비율 |
| 리스크 | mrkt_warn_cls_code | 시장경고 코드 |
| | invt_caful_yn | 투자유의 여부 |
| | short_over_yn | 단기과열 여부 |

### 8.2 주문 이력 테이블

#### LLM 판단 이력 테이블

- 요청 프롬프트 원문, 응답 원문 저장
- 파싱된 결정(JSON), 처리 시간(ms), 에러 여부 저장

#### LLM 주문 이력 테이블

- HOLD가 아닌 경우 주문 실행 후 이력 저장
- 주문 종목/가격/수량, 주문 결과, 판단 이력 FK 저장
- 가상 주문 단계: 주문 필드 = 결과 필드 (즉시 체결)
- 실거래 연동 단계: 주문 후 체결 응답으로 결과 필드 업데이트

### 8.3 자산 테이블

- 현재 보유 주식: 종목코드, 수량, 주당 금액, 총금액 등
- 현금: 종목코드 null, 수량 1, 주당금액 = 총금액 = 현재 남은 현금

## 9. LLM 요청 규격

### 9.1 뉴스 요약

뉴스 테이블의 URL로 본문을 크롤링한 뒤 LLM에 질의한다.

프롬프트:
```
아래는 뉴스 본문이다. 이걸 요약하고 주식 단타에 도움이 되는지 판단 후,
{"summary": "...", "useful": true} 형태로 응답 해달라.

<뉴스 본문>
...
```

### 9.2 매수 판단

- 자산 테이블 기준으로 보유 종목이 없을 때 실행한다.
- 프롬프트 포함 데이터:
  - 10개 종목별 정보
    - Redis 체결/호가 기반 최근 10분 가격 흐름
    - 자산 테이블 잔액
    - 종목 현재 정보 최신 row (프롬프트 포함 필드 15개)
    - 최근 7일 다트 공시
    - 최근 10건 뉴스 (useful=true 또는 useful is null인 것만)
  - 각 데이터의 수집 시간을 포함하여 LLM이 시간 경과를 판단할 수 있도록 한다.

프롬프트:
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

### 9.3 매도 판단

- 보유 종목이 있을 때 실행한다.
- 요청/응답 형식은 매수 판단과 동일하되, 1개 종목 정보만 전달한다.
- 매수/매도 프롬프트에는 "가급적 단타(익절 중심)" 원칙을 포함한다.

### 9.4 LLM 요청 함수

공통 함수 `ask_llm(...: Any) -> json | str`를 사용하며, `nanobot`을 호출한다.

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

### 9.5 LLM 실패 처리

- LLM 응답 파싱(JSON) 실패, 타임아웃, 빈 응답 등 비정상 케이스는 기본적으로 HOLD 처리한다.
- 실패 내역은 판단 이력 테이블에 에러 여부/원문 응답과 함께 저장한다.

## 10. 운영 명령(Makefile) 및 모니터링

### 10.1 필수 Makefile 타겟

| 타겟 | 설명 |
| --- | --- |
| systemd-install | 모든 systemd unit/timer 설치 및 enable |
| systemd-remove | 모든 systemd unit/timer 비활성화 및 제거 |
| systemd-restart | 실패 상태(failed) 유닛만 재시작 |
| systemd-status | 서비스/타이머 상태 요약 출력 |
| systemd-timers | 타이머 스케줄 목록 출력 |
| systemd-overview | systemd-status + systemd-timers 출력 |
| check | TESTS.md 기준 테스트 실행, 성공 시 종료코드 1 / 실패 시 0 반환 |

> systemd 실행 커맨드는 반드시 절대 경로로 실행한다.
> `make check`는 AI 종료 조건이며 구현한 통합테스트들을 모두 실행해야 한다.

### 10.2 모니터링 방법

- 타이머 실행 여부 확인: `systemctl list-timers` (LAST/NEXT 갱신 확인)
- 서비스 상태 확인: `systemctl status alt-<name>` / 타이머: `systemctl status alt-<name>.timer`
- 로그 확인: `journalctl -u alt-<name>.service -n 200 --no-pager`
- 실시간 추적: `journalctl -u alt-<name>.service -f`

### 10.3 대상 서비스(타이머)

| 서비스 | 주기 |
| --- | --- |
| alt-news | 매 5분 |
| alt-dart | 매 10분 |
| alt-market-realtime | 평일 09:00~15:30, 매 1분 |

### 10.4 대상 서비스(상주)

| 서비스 | 설명 |
| --- | --- |
| alt-ws-subscribe | 웹소켓 구독 상주 서비스 |
| alt-trader | 트레이딩 서비스 (평일 09:10~15:30, 1회성 커맨드 + Restart=always) |

## 11. 결정 사항

### 11.1 도메인 앱

| 앱 | 역할 |
| --- | --- |
| news | 뉴스 수집 |
| dart | 공시 수집 |
| market | 시세/종목 정보 수집 |
| trader | 매수/매도 판단 및 주문 |
| ws | 웹소켓 구독 |
| asset | 자산(잔고/보유주식) 관리 |

### 11.2 공통 모듈

- `ask_llm` 등 LLM 관련 공통 로직은 shared 구조에서 관리한다. (별도 컨벤션 문서에서 정의)

### 11.3 API 범위

- 초기에는 API를 제공하지 않는다. (관리/조회 목적 API는 추후 결정)

### 11.4 시간 기준

- 모든 시간은 KST 고정 기준
- 휴장일은 초기 범위에서 제외하고, 월~금 스케줄만 적용
