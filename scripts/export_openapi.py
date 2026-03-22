import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.app.main import app

schema = app.openapi()
out = Path("docs/openapi.json")
out.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅ {out} 저장 완료 ({len(schema.get('paths', {}))}개 경로)")
