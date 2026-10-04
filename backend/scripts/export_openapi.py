import json
from pathlib import Path

from app.main import app

target = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print(target)
