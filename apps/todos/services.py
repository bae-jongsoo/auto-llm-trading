from typing import Optional

from django.conf import settings

from apps.todos.models import Todo
from shared.external.telegram import send_message as send_telegram


class TodoNotFoundError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


VALID_TRANSITIONS: dict[str, list[str]] = {
    Todo.Status.TODO: [Todo.Status.IN_PROGRESS],
    Todo.Status.IN_PROGRESS: [Todo.Status.DONE, Todo.Status.TODO],
    Todo.Status.DONE: [],
}


def create_todo(title: str, description: str = "") -> Todo:
    if not title.strip():
        raise ValueError("제목은 비어있을 수 없습니다")
    return Todo.objects.create(title=title.strip(), description=description)


def get_todo(todo_id: int) -> Todo:
    try:
        return Todo.objects.get(id=todo_id)
    except Todo.DoesNotExist:
        raise TodoNotFoundError(f"TODO를 찾을 수 없습니다: {todo_id}")


def list_todos(status: Optional[str] = None) -> list[Todo]:
    qs = Todo.objects.all()
    if status:
        qs = qs.filter(status=status)
    return list(qs)


def update_todo(todo_id: int, title: Optional[str] = None, description: Optional[str] = None) -> Todo:
    todo = get_todo(todo_id)
    if title is not None:
        if not title.strip():
            raise ValueError("제목은 비어있을 수 없습니다")
        todo.title = title.strip()
    if description is not None:
        todo.description = description
    todo.save()
    return todo


def change_status(todo_id: int, new_status: str) -> Todo:
    todo = get_todo(todo_id)
    _validate_status_transition(todo.status, new_status)
    todo.status = new_status
    todo.save()

    if new_status == Todo.Status.DONE:
        send_telegram(settings.TELEGRAM_DEFAULT_CHAT_ID, f"TODO 완료: {todo.title}")

    return todo


def delete_todo(todo_id: int) -> None:
    todo = get_todo(todo_id)
    todo.delete()


def _validate_status_transition(current_status: str, new_status: str) -> None:
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise InvalidStatusTransitionError(
            f"{current_status}에서 {new_status}로 변경할 수 없습니다"
        )
