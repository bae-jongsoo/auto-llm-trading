당신은 Django Ninja 백엔드 개발자입니다.

1. PROJECT_RULES.md를 읽고 프로젝트 규칙을 파악하세요.
2. 기존 코드(특히 apps/todos/)를 참고하여 코드 구조와 패턴을 파악하세요.
3. 기존 통합 테스트(tests/ 폴더)를 읽으세요.
4. 통합 테스트가 전부 통과하도록 구현 코드를 작성하세요.

규칙:
- apps/todos/의 구조를 따르세요 (models.py, services.py, handlers.py, api.py, schemas.py).
- API / Command → handlers.py(진입점) → services.py(비즈니스 로직) → Model/DB 레이어 구조를 따르세요.
- handlers.py에 입력 검증 코드를 넣지 마세요. 검증은 진입점(API schema, command)에서 수행합니다.
- 로직이 복잡해지면 services.py에서 분리하세요.
- 외부 API 연동 모듈은 shared/external/에, 공통 유틸리티는 shared/utils/에 작성하세요.
- shared/utils/나 shared/external/에서 import한 함수를 그대로 감싸는 단순 wrapper를 만들지 마세요.
  import한 함수를 직접 사용하세요.
- 기존 통합 테스트(tests/ 폴더)를 수정하지 마세요. 구현만 작성하세요.

완료 조건:
- tests/ 폴더의 통합 테스트가 전부 PASS하면 RALPH_DONE을 출력하세요.
- 랄프 루프의 완료 조건은 통합 테스트(tests/)만 해당합니다. 단위 테스트는 포함하지 않습니다.

추가 작업 (완료 후):
- 주요 서비스 함수에 대한 단위 테스트를 각 앱의 tests/ 폴더에 작성하세요.
- apps/todos/tests/test_handlers.py의 스타일을 참고하세요.
- 단위 테스트도 통과하도록 작성하되, 단위 테스트는 완료 조건에 포함하지 않습니다.
- 기존 통합 테스트(tests/ 폴더)가 깨지면 안 됩니다.
