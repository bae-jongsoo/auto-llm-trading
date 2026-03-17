from unittest.mock import MagicMock, patch

import pytest
from apps.todos.models import Todo
from apps.todos.services import (
    InvalidStatusTransitionError,
    TodoNotFoundError,
    change_status,
    create_todo,
    delete_todo,
    get_todo,
    list_todos,
    update_todo,
)


# ──────────────────────────────────────
# Fixtures
# ──────────────────────────────────────

@pytest.fixture
def mock_telegram():
    """텔레그램 알림 발송을 mock한다. 외부 API mock의 표준 패턴."""
    with patch("apps.todos.services.send_telegram") as mock_send:
        mock_send.return_value = MagicMock(status_code=200)
        yield mock_send


# ──────────────────────────────────────
# 생성
# ──────────────────────────────────────

@pytest.mark.django_db
def test_할일_생성_성공():
    todo = create_todo(title="보고서 작성", description="월간 보고서")
    assert todo.id is not None
    assert todo.title == "보고서 작성"
    assert todo.description == "월간 보고서"
    assert todo.status == Todo.Status.TODO


@pytest.mark.django_db
def test_할일_생성_빈_제목_실패():
    with pytest.raises(ValueError, match="비어있을 수 없습니다"):
        create_todo(title="")


@pytest.mark.django_db
def test_할일_생성_공백만_제목_실패():
    with pytest.raises(ValueError, match="비어있을 수 없습니다"):
        create_todo(title="   ")


# ──────────────────────────────────────
# 조회
# ──────────────────────────────────────

@pytest.mark.django_db
def test_할일_조회_성공():
    todo = create_todo(title="테스트")
    found = get_todo(todo.id)
    assert found.id == todo.id
    assert found.title == "테스트"


@pytest.mark.django_db
def test_할일_조회_없는_ID_실패():
    with pytest.raises(TodoNotFoundError):
        get_todo(99999)


@pytest.mark.django_db
def test_할일_목록_전체_조회():
    create_todo(title="A")
    create_todo(title="B")
    create_todo(title="C")
    todos = list_todos()
    assert len(todos) == 3


@pytest.mark.django_db
def test_할일_목록_상태_필터():
    create_todo(title="A")
    todo_b = create_todo(title="B")
    change_status(todo_b.id, Todo.Status.IN_PROGRESS)

    todo_only = list_todos(status=Todo.Status.TODO)
    assert len(todo_only) == 1
    assert todo_only[0].title == "A"


# ──────────────────────────────────────
# 수정
# ──────────────────────────────────────

@pytest.mark.django_db
def test_할일_제목_수정():
    todo = create_todo(title="원래 제목")
    updated = update_todo(todo.id, title="바뀐 제목")
    assert updated.title == "바뀐 제목"


@pytest.mark.django_db
def test_할일_수정_빈_제목_실패():
    todo = create_todo(title="원래 제목")
    with pytest.raises(ValueError, match="비어있을 수 없습니다"):
        update_todo(todo.id, title="")


@pytest.mark.django_db
def test_할일_수정_없는_ID_실패():
    with pytest.raises(TodoNotFoundError):
        update_todo(99999, title="없는 할일")


# ──────────────────────────────────────
# 상태 변경
# ──────────────────────────────────────

@pytest.mark.django_db
def test_상태변경_TODO에서_IN_PROGRESS():
    todo = create_todo(title="테스트")
    updated = change_status(todo.id, Todo.Status.IN_PROGRESS)
    assert updated.status == Todo.Status.IN_PROGRESS


@pytest.mark.django_db
def test_상태변경_IN_PROGRESS에서_DONE(mock_telegram):
    todo = create_todo(title="테스트")
    change_status(todo.id, Todo.Status.IN_PROGRESS)
    updated = change_status(todo.id, Todo.Status.DONE)
    assert updated.status == Todo.Status.DONE


@pytest.mark.django_db
def test_상태변경_TODO에서_DONE_불가():
    todo = create_todo(title="테스트")
    with pytest.raises(InvalidStatusTransitionError):
        change_status(todo.id, Todo.Status.DONE)


@pytest.mark.django_db
def test_상태변경_DONE에서_변경_불가(mock_telegram):
    todo = create_todo(title="테스트")
    change_status(todo.id, Todo.Status.IN_PROGRESS)
    change_status(todo.id, Todo.Status.DONE)
    with pytest.raises(InvalidStatusTransitionError):
        change_status(todo.id, Todo.Status.TODO)


@pytest.mark.django_db
def test_상태변경_IN_PROGRESS에서_TODO_복귀():
    todo = create_todo(title="테스트")
    change_status(todo.id, Todo.Status.IN_PROGRESS)
    updated = change_status(todo.id, Todo.Status.TODO)
    assert updated.status == Todo.Status.TODO


# ──────────────────────────────────────
# 알림 (외부 API mock 예시)
# ──────────────────────────────────────

@pytest.mark.django_db
def test_DONE_변경_시_텔레그램_알림_발송(mock_telegram):
    todo = create_todo(title="알림 테스트")
    change_status(todo.id, Todo.Status.IN_PROGRESS)

    change_status(todo.id, Todo.Status.DONE)

    mock_telegram.assert_called_once()
    chat_id, message = mock_telegram.call_args[0]
    assert chat_id is not None
    assert "알림 테스트" in message


@pytest.mark.django_db
def test_텔레그램_알림_실패해도_상태변경은_성공():
    with patch("apps.todos.services.send_telegram", return_value=None):
        todo = create_todo(title="알림 실패 테스트")
        change_status(todo.id, Todo.Status.IN_PROGRESS)

        updated = change_status(todo.id, Todo.Status.DONE)

        assert updated.status == Todo.Status.DONE


@pytest.mark.django_db
def test_DONE_아닌_상태변경_시_알림_미발송(mock_telegram):
    todo = create_todo(title="알림 없음 테스트")

    change_status(todo.id, Todo.Status.IN_PROGRESS)

    mock_telegram.assert_not_called()


# ──────────────────────────────────────
# 삭제
# ──────────────────────────────────────

@pytest.mark.django_db
def test_할일_삭제_성공():
    todo = create_todo(title="삭제 대상")
    delete_todo(todo.id)
    with pytest.raises(TodoNotFoundError):
        get_todo(todo.id)


@pytest.mark.django_db
def test_할일_삭제_없는_ID_실패():
    with pytest.raises(TodoNotFoundError):
        delete_todo(99999)
