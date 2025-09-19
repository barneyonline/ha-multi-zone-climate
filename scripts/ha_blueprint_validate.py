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
from types import ModuleType


def _ensure_stub_notifications() -> None:
    """Stub persistent notifications to avoid circular imports.

    Loading Home Assistant's blueprint helpers pulls in config entries, which in
    turn import the persistent_notification component. In a minimal standalone
    environment (like this validator), that import chain fails because
    persistent_notification depends on parts of Home Assistant that expect the
    full runtime. We provide a tiny stub with the async helpers used during the
    import sequence so the real blueprint schema can still load.
    """

    module_name = "homeassistant.components.persistent_notification"
    if module_name in sys.modules:
        return

    stub = ModuleType(module_name)

    async def _noop_async(*_args, **_kwargs):
        return None

    def _noop_sync(*_args, **_kwargs):
        return None

    stub.async_create = _noop_async
    stub.async_dismiss = _noop_async
    stub.create = _noop_sync
    stub.dismiss = _noop_sync
    sys.modules[module_name] = stub


_ensure_stub_notifications()

from homeassistant.components.blueprint.errors import BlueprintException
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.util import yaml as yaml_util


async def validate_one(path: Path) -> bool:
    """Validate a single blueprint file."""
    try:
        # Parse YAML (supports Home Assistant tags like !input)
        data = yaml_util.load_yaml(path)
        # Validate against the official blueprint schema
        Blueprint(data, path=str(path))
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
