from django.core.management.base import BaseCommand

from apps.todos import services
from apps.todos.models import Todo


class Command(BaseCommand):
    help = "TODO 목록을 조회합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            type=str,
            choices=[s.value for s in Todo.Status],
            help="상태로 필터링 (TODO, IN_PROGRESS, DONE)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="조회 건수 (기본: 20)",
        )

    def handle(self, *args, **options):
        status = options["status"]
        limit = options["limit"]

        todos = services.list_todos(status=status)[:limit]

        if not todos:
            self.stdout.write("조회된 TODO가 없습니다.")
            return

        self.stdout.write(f"총 {len(todos)}건")
        self.stdout.write("-" * 60)

        for todo in todos:
            self.stdout.write(
                f"[{todo.status:12s}] {todo.title} (id={todo.id})"
            )
