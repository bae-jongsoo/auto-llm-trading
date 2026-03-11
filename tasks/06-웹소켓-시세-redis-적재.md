# 06. 웹소켓 시세 Redis 적재

## 개요
웹소켓 체결/호가 데이터를 Redis에 저장하고, 최근 1시간 윈도우만 유지하는 서비스를 구현한다.
트레이더가 사용하는 최근 10분 가격 흐름 조회 함수를 함께 제공한다.

## 테스트 대상 함수
- `shared/external/kis_ws.py::build_ws_subscribe_messages(stock_code: str) -> list[dict]`
- `apps/ws/services.py::save_trade_tick(stock_code: str, tick: dict, now: datetime | None = None) -> None`
- `apps/ws/services.py::save_quote_tick(stock_code: str, tick: dict, now: datetime | None = None) -> None`
- `apps/ws/services.py::trim_ticks(stock_code: str, now: datetime | None = None) -> None`
- `apps/ws/services.py::get_recent_price_flow(stock_code: str, minutes: int = 10) -> dict`

## 진입점(있는 경우)
- management command: `ws_subscribe`
- 인자: 없음
- 옵션: 없음

## 비즈니스 규칙
1. 대상 10종목만 구독/저장한다.
2. 체결 데이터와 호가 데이터는 Redis 키를 분리해 저장한다.
3. 저장 시점마다 1시간 이전 데이터는 삭제한다.
4. 최근 10분 조회 함수는 시간순 정렬된 데이터로 반환한다.
5. 트레이딩 프롬프트에 포함 가능한 형태(가격 흐름 + 수집시각)로 가공한다.
6. 시간 처리는 KST 기준 운영 정책을 따른다.

## 에러 케이스
- 지원하지 않는 종목코드
- Redis 연결 실패
- 웹소켓 메시지 필수 필드 누락
- 비정상 메시지(JSON 파싱 실패 등)
- 연결 끊김/재연결 시 중복 데이터 처리

## 참고
- 저장소: Redis (`CACHES["default"]`)
- 환경변수: `REDIS_URL`, KIS 웹소켓 접속에 필요한 인증 관련 변수
- 정책: 최신 1시간만 보관
