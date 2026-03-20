run-backend:
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python -m uvicorn api.main:app; \
	else \
		python -m uvicorn api.main:app; \
	fi

run-frontend:
	cd frontend && npm run dev -- --host

run-all:
	@echo "Starting backend and frontend (use separate terminals for logs)"
	@$(MAKE) run-backend & $(MAKE) run-frontend
