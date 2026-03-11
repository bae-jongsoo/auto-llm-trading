from typing import Optional

from ninja import Router

from apps.todos import services
from apps.todos.schemas import TodoCreateIn, TodoOut, TodoStatusIn, TodoUpdateIn

router = Router()


@router.post("/", response={201: TodoOut})
def create_todo(request, payload: TodoCreateIn):
    todo = services.create_todo(title=payload.title, description=payload.description)
    return 201, todo


@router.get("/", response=list[TodoOut])
def list_todos(request, status: Optional[str] = None):
    return services.list_todos(status=status)


@router.get("/{todo_id}/", response=TodoOut)
def get_todo(request, todo_id: int):
    return services.get_todo(todo_id)


@router.put("/{todo_id}/", response=TodoOut)
def update_todo(request, todo_id: int, payload: TodoUpdateIn):
    return services.update_todo(
        todo_id, title=payload.title, description=payload.description
    )


@router.post("/{todo_id}/status/", response=TodoOut)
def change_status(request, todo_id: int, payload: TodoStatusIn):
    return services.change_status(todo_id, new_status=payload.status)


@router.delete("/{todo_id}/", response={204: None})
def delete_todo(request, todo_id: int):
    services.delete_todo(todo_id)
    return 204, None
