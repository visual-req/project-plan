from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn


def main() -> None:
    default_config = os.environ.get("PROJECT_PLAN_CONFIG")
    if not default_config:
        root = Path.cwd().resolve()
        if (root / "backend" / "config.yaml").exists():
            default_config = str((root / "backend" / "config.yaml").resolve())
        elif (root / "config.yaml").exists():
            default_config = str((root / "config.yaml").resolve())

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8010")))
    parser.add_argument("--config", dest="config_path", default=default_config)
    args = parser.parse_args()

    if args.config_path:
        os.environ["PROJECT_PLAN_CONFIG"] = args.config_path

    uvicorn.run("backend.main:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
