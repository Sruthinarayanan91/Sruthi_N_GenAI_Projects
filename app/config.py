import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
SUPPLIER_DIR = DATA_DIR / "suppliers"
DB_PATH = DATA_DIR / "rfp_evaluation.db"
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
