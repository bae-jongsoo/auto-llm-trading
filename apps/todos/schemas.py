from datetime import datetime
from typing import Optional

from ninja import Schema


class TodoCreateIn(Schema):
    title: str
    description: str = ""


class TodoUpdateIn(Schema):
    title: Optional[str] = None
    description: Optional[str] = None


class TodoStatusIn(Schema):
    status: str


class TodoOut(Schema):
    id: int
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
