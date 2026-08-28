import json
from pathlib import Path
from typing import Any


def sample_packet() -> dict[str, Any]:
    path = Path(__file__).parents[1] / "examples" / "research-packet.json"
    return json.loads(path.read_text(encoding="utf-8"))
