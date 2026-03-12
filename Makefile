PROJECT_DIR := $(shell pwd)
VENV_PYTHON := $(PROJECT_DIR)/.venv/bin/python
MANAGE := $(VENV_PYTHON) $(PROJECT_DIR)/manage.py

# launchd (macOS)
LAUNCH_AGENTS := $(HOME)/Library/LaunchAgents
PLIST_LABELS := com.alt.news com.alt.dart com.alt.market-realtime com.alt.ws-subscribe com.alt.trader

# systemd (Linux)
SYSTEMD_DIR := /etc/systemd/system
TIMER_SERVICES := alt-news alt-dart alt-market-realtime
PERSISTENT_SERVICES := alt-ws-subscribe alt-trader
ALL_SERVICES := $(TIMER_SERVICES) $(PERSISTENT_SERVICES)

.PHONY: help check migrate install remove restart status logs

help: ## 사용 가능한 타겟 목록
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F ':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────
# 개발
# ──────────────────────────────────────

check: ## 테스트 실행
	$(VENV_PYTHON) -m pytest -q tests/

migrate: ## DB 마이그레이션
	$(MANAGE) migrate

# ──────────────────────────────────────
# 서비스 (플랫폼 자동 감지)
# ──────────────────────────────────────

install: ## 서비스 설치 (launchd/systemd)
ifeq ($(shell uname),Darwin)
	@mkdir -p $(PROJECT_DIR)/logs
	@for f in launchd/*.plist; do \
		sed -e 's|__PROJECT_DIR__|$(PROJECT_DIR)|g' \
		    -e 's|__VENV_PYTHON__|$(VENV_PYTHON)|g' \
		    "$$f" > $(LAUNCH_AGENTS)/$$(basename "$$f"); \
		launchctl load $(LAUNCH_AGENTS)/$$(basename "$$f"); \
	done
	@echo "launchd 설치 완료"
else
	@for f in systemd/*.service systemd/*.timer; do \
		sed -e 's|__PROJECT_DIR__|$(PROJECT_DIR)|g' \
		    -e 's|__VENV_PYTHON__|$(VENV_PYTHON)|g' \
		    "$$f" | sudo tee $(SYSTEMD_DIR)/$$(basename "$$f") > /dev/null; \
	done
	sudo systemctl daemon-reload
	@for svc in $(TIMER_SERVICES); do \
		sudo systemctl enable --now $$svc.timer; \
	done
	@for svc in $(PERSISTENT_SERVICES); do \
		sudo systemctl enable --now $$svc.service; \
	done
	@echo "systemd 설치 완료"
endif

remove: ## 서비스 제거
ifeq ($(shell uname),Darwin)
	@for label in $(PLIST_LABELS); do \
		launchctl unload $(LAUNCH_AGENTS)/$$label.plist 2>/dev/null || true; \
		rm -f $(LAUNCH_AGENTS)/$$label.plist; \
	done
	@echo "launchd 제거 완료"
else
	@for svc in $(TIMER_SERVICES); do \
		sudo systemctl disable --now $$svc.timer 2>/dev/null || true; \
		sudo systemctl stop $$svc.service 2>/dev/null || true; \
	done
	@for svc in $(PERSISTENT_SERVICES); do \
		sudo systemctl disable --now $$svc.service 2>/dev/null || true; \
	done
	@for svc in $(ALL_SERVICES); do \
		sudo rm -f $(SYSTEMD_DIR)/$$svc.service $(SYSTEMD_DIR)/$$svc.timer; \
	done
	sudo systemctl daemon-reload
	@echo "systemd 제거 완료"
endif

restart: ## 서비스 재시작
ifeq ($(shell uname),Darwin)
	@for label in $(PLIST_LABELS); do \
		launchctl unload $(LAUNCH_AGENTS)/$$label.plist 2>/dev/null || true; \
		launchctl load $(LAUNCH_AGENTS)/$$label.plist 2>/dev/null || true; \
	done
	@echo "재시작 완료"
else
	@for svc in $(TIMER_SERVICES); do \
		sudo systemctl restart $$svc.timer; \
	done
	@for svc in $(PERSISTENT_SERVICES); do \
		sudo systemctl restart $$svc.service; \
	done
	@echo "재시작 완료"
endif

status: ## 서비스 상태 확인
ifeq ($(shell uname),Darwin)
	@for label in $(PLIST_LABELS); do \
		echo "── $$label ──"; \
		launchctl list $$label 2>/dev/null || echo "  not loaded"; \
		echo ""; \
	done
else
	@for svc in $(ALL_SERVICES); do \
		echo "── $$svc ──"; \
		systemctl status $$svc.service --no-pager -l 2>/dev/null || true; \
		echo ""; \
	done
endif

logs: ## 최근 로그 출력
ifeq ($(shell uname),Darwin)
	@echo "=== 최근 로그 ==="
	@for label in $(PLIST_LABELS); do \
		name=$$(echo $$label | sed 's/com\.alt\.//'); \
		echo "── $$name ──"; \
		tail -5 $(PROJECT_DIR)/logs/$$name.log 2>/dev/null || echo "  (없음)"; \
		echo ""; \
	done
else
	@for svc in $(ALL_SERVICES); do \
		echo "── $$svc ──"; \
		journalctl -u $$svc.service -n 10 --no-pager 2>/dev/null || true; \
		echo ""; \
	done
endif
