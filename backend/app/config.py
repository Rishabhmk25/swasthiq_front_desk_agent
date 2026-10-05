"""Configuration from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CLINIC_JSON = BASE_DIR.parent / "data" / "clinic.json"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "none")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# DB for conversation logs (separate from per-run clinic state)
LOGS_DB_PATH = os.getenv("LOGS_DB_PATH", str(BASE_DIR.parent / "logs.db"))
