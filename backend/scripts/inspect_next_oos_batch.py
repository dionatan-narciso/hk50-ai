from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.oos_validation.forward_dataset import inspect_next_batch


def main() -> None:
    print(json.dumps(inspect_next_batch(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
