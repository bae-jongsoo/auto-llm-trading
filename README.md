# ALT - AI LLM Trader

한국 주식 자동 단타 트레이딩 시스템. LLM이 실시간 시세, 뉴스, 공시, 분봉 데이터를 종합 분석하여 매수/매도를 판단하고 가상 주문을 실행합니다.

## 구조

```
apps/
  trader/    트레이딩 사이클 (LLM 판단 → 주문 실행)
  market/    시장 스냅샷 수집 (KIS API)
  ws/        실시간 체결 틱 수집 (KIS WebSocket) + 분봉 집계
  news/      뉴스 수집 및 LLM 요약
  dart/      DART 공시 수집
  asset/     가상 자산 관리 (현금/포지션)
  todos/     할일 관리
shared/
  external/  외부 API 연동 (KIS, LLM, Telegram)
  stock_universe.py  대상 종목 관리
```

## 기술 스택

- Python 3.12+ / Django 5.1+
- PostgreSQL / Redis
- KIS Open API (PyKIS)
- nanobot (LLM CLI)
- launchd (macOS) / systemd (Linux)

## 설치

```bash
# 의존성 설치
uv sync

# DB 마이그레이션
uv run python manage.py migrate

# 서비스 등록 (launchd/systemd)
make install
```

## 서비스

| 서비스 | 주기 | 설명 |
|--------|------|------|
| news | 5분 | 뉴스 수집 + LLM 요약 |
| dart | 10분 | DART 공시 수집 |
| market-realtime | 연속 | 시장 스냅샷 수집 (08:58~15:32) |
| ws-subscribe | 연속 | 실시간 체결 틱 수집 (08:58~15:32) |
| trader | 1분 | 트레이딩 사이클 (09:11~15:30) |

## 명령어

```bash
make install   # 서비스 설치
make remove    # 서비스 제거
make restart   # 서비스 재시작
make status    # 서비스 상태 확인
make logs      # 최근 로그 출력
```

## 모델

### 데이터 수집
| 모델 | 앱 | 설명 |
|------|-----|------|
| MarketSnapshot | market | 종목별 시장 지표 스냅샷 (PER, PBR, 외인비율 등) |
| News | news | 종목별 뉴스 (LLM 요약 + 유용성 판단) |
| DartDisclosure | dart | DART 공시 |
| MinuteCandle | ws | 1분봉 OHLCV (Redis 틱 집계) |

### 트레이딩
| 모델 | 앱 | 설명 |
|------|-----|------|
| DecisionHistory | trader | LLM 판단 이력 (요청/응답/파싱결과) |
| OrderHistory | trader | 주문 실행 이력 (매수/매도) |
| Asset | asset | 가상 자산 (현금 + 보유 포지션) |

### 기타
| 모델 | 앱 | 설명 |
|------|-----|------|
| Todo | todos | 할일 관리 |

## 테스트

```bash
uv run pytest tests/ -x -q
```
