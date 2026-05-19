from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import summarize_status  # noqa: E402


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    print(json.dumps(summarize_status(config_path), ensure_ascii=False, indent=2, sort_keys=True))
