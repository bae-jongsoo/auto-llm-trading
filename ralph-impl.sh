#!/bin/bash
# ralph-impl.sh — 2차 루프: 테스트 통과하는 구현 코드 생성
# 사용법: ./ralph-impl.sh <태스크파일> [최대반복]

TASK_FILE="${1:?태스크 파일 경로 필요}"
MAX_ITER="${2:-20}"

exec ./ralph-loop.sh .ralph/prompt-implement.md "$TASK_FILE" "$MAX_ITER"
