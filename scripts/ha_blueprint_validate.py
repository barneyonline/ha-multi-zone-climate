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

from homeassistant.components.blueprint.errors import BlueprintException
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.util import yaml as yaml_util


async def validate_one(path: Path) -> bool:
    """Validate a single blueprint file."""
    try:
        # Parse YAML (supports Home Assistant tags like !input)
        data = yaml_util.load_yaml(path)
        # Validate against the official blueprint schema
        Blueprint(data, path=str(path), schema=BLUEPRINT_SCHEMA)
        print(f"✅ {path} — valid")
        return True
    except BlueprintException as err:
        print(f"❌ {path}\n    {err}", file=sys.stderr)
        return False
    except Exception as err:  # pylint: disable=broad-except
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
