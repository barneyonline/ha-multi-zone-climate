#!/usr/bin/env python3
"""
Validate one or more Home Assistant blueprints using Home Assistant Core’s
built-in blueprint loader (same logic the UI uses).
Example:

    python ha_blueprint_validate.py blueprints/**/*.yaml
"""
import asyncio
import sys
from pathlib import Path

from homeassistant.helpers.blueprint import load_blueprint, BlueprintException

async def validate_one(path: Path) -> bool:
    try:
        # This parses YAML, resolves !input, and runs the voluptuous schema
        await load_blueprint(path.read_text(), path)
        print(f"✅ {path} — valid")
        return True
    except BlueprintException as err:
        print(f"❌ {path}\n    {err}", file=sys.stderr)
        return False

async def main(paths):
    ok = True
    for p in paths:
        if not await validate_one(Path(p)):
            ok = False
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No blueprint files given", file=sys.stderr)
        sys.exit(2)
    asyncio.run(main(sys.argv[1:]))
