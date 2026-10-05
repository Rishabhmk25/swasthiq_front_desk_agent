.PHONY: run run-unix run-windows test determinism

run:
	@echo "Please use 'make run-unix' or 'make run-windows'"

run-unix:
	@echo "Starting backend and frontend (Unix)..."
	@if [ ! -d "venv" ]; then python3 -m venv venv; fi
	@. venv/bin/activate && pip install -q -r backend/requirements.txt
	@cd frontend && npm install --silent
	@. venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend &
	@cd frontend && npm run dev &
	@echo "Backend: http://localhost:8000  Frontend: http://localhost:5173"

run-windows:
	@echo "Starting backend and frontend (Windows)..."
	@if not exist venv (python -m venv venv)
	@venv\Scripts\activate.bat && pip install -q -r backend\requirements.txt
	@cd frontend && npm install --silent
	@start cmd /c "cd frontend && npm run dev"
	@venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend

test-unix:
	@venv/bin/pytest backend/tests/ -v

test-windows:
	@venv\Scripts\pytest backend\tests\ -v

grade-unix:
	@venv/bin/python runner.py --repeat 1
	@venv/bin/python backend/scripts/grade.py

grade-windows:
	@venv\Scripts\python runner.py --repeat 1
	@venv\Scripts\python backend\scripts\grade.py

determinism-unix:
	@venv/bin/python runner.py --repeat 3

determinism-windows:
	@venv\Scripts\python runner.py --repeat 3
