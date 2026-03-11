#!/bin/bash
# ralph-loop.sh — Codex CLI로 랄프 루프 실행
# 사용법: ./ralph-loop.sh <프롬프트파일> <태스크파일> [최대반복]

set -euo pipefail

PROMPT_FILE="${1:?프롬프트 파일 경로 필요}"
TASK_FILE="${2:?태스크 파일 경로 필요}"
MAX_ITER="${3:-20}"
ITER=0
LOG=".ralph/activity.log"
STAGE="test"

if [ "$(basename "$PROMPT_FILE")" = "prompt-implement.md" ]; then
  STAGE="implementation"
fi

mkdir -p .ralph

[ -f "$PROMPT_FILE" ] || { echo "❌ $PROMPT_FILE 없음"; exit 1; }
[ -f "$TASK_FILE" ] || { echo "❌ $TASK_FILE 없음"; exit 1; }
[ -f "PROJECT_RULES.md" ] || { echo "❌ PROJECT_RULES.md 없음"; exit 1; }
command -v codex &>/dev/null || { echo "❌ codex CLI 없음"; exit 1; }

echo "📋 프롬프트: $PROMPT_FILE"
echo "📋 태스크: $TASK_FILE"
echo "🔁 최대 반복: $MAX_ITER"
echo "---"

while [ $ITER -lt $MAX_ITER ]; do
  ITER=$((ITER + 1))
  TS=$(date '+%Y-%m-%d %H:%M:%S')
  echo ""
  echo "=== [$TS] Iteration $ITER / $MAX_ITER ==="
  echo "[$TS] Iteration $ITER" >> "$LOG"

  FULL_PROMPT="$(cat "$PROMPT_FILE")

[태스크 스펙]
$(cat "$TASK_FILE")

[루프 메타]
- 단계: $STAGE
- iteration: $ITER / $MAX_ITER
- activity_log: $LOG

[현재 프로젝트 상태]
$(git log --oneline -5 2>/dev/null || echo '커밋 없음')"

  RESULT=$(codex exec --full-auto -s danger-full-access "$FULL_PROMPT" 2>&1) || true
  echo "$RESULT" >> "$LOG"

  if echo "$RESULT" | grep -q "RALPH_DONE"; then
    echo "✅ 완료"
    git add -A && git commit -m "Ralph 완료: $TASK_FILE (iter $ITER)" 2>/dev/null || true
    exit 0
  fi

  git add -A && git commit -m "Ralph 진행: $TASK_FILE (iter $ITER)" 2>/dev/null || true
  echo "🔄 다음 iteration..."
done

echo "❌ 최대 반복 도달. .ralph/activity.log 확인."
exit 1
