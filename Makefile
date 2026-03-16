run-backend:
	source .venv/bin/activate && python -m uvicorn api.main:app --reload

run-frontend:
	cd frontend && npm run dev -- --host

run-all:
	@echo "Starting backend and frontend (use separate terminals for logs)"
	@$(MAKE) run-backend & $(MAKE) run-frontend
