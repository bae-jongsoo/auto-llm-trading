#!/bin/bash
# ralph-test.sh — 1차 루프: 태스크 스펙 기반 테스트 코드 생성
# 사용법: ./ralph-test.sh <태스크파일> [최대반복]

TASK_FILE="${1:?태스크 파일 경로 필요}"
MAX_ITER="${2:-10}"

exec ./ralph-loop.sh .ralph/prompt-test-gen.md "$TASK_FILE" "$MAX_ITER"
