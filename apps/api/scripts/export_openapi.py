"""Write apps/api/openapi.json from the FastAPI app."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "openapi.json"
    schema = app.openapi()
    output.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
