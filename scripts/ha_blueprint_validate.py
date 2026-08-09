#!/usr/bin/env python3
"""
Validate one or more Home Assistant blueprints using Home Assistant Core’s
built-in blueprint loader (same logic the UI uses).
Example:

    python ha_blueprint_validate.py blueprints/**/*.yaml
"""
# Home Assistant imports must follow the standalone compatibility shims below.
# ruff: noqa: E402

import asyncio
import inspect
import sys
from pathlib import Path
from types import ModuleType


def _ensure_stub_notifications() -> None:
    """Provide a minimal persistent_notification stub when running standalone."""

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


def _ensure_pycares_compat() -> None:
    """Patch missing legacy pycares result types used by older aiodns releases.

    Home Assistant imports aiohttp during blueprint validation. Some resolver
    combinations in CI install `aiodns` 3.x alongside newer `pycares` versions
    where legacy type aliases like `ares_query_a_result` no longer exist.
    Those names are only used for import-time type annotations, so a lightweight
    shim is sufficient for validation.
    """

    try:
        import pycares  # type: ignore
    except ImportError:
        return

    if hasattr(pycares, "ares_query_a_result"):
        return

    def _compat_getattr(name: str):
        if name.startswith("ares_") and name.endswith("_result"):
            placeholder = type(name, (), {})
            setattr(pycares, name, placeholder)
            return placeholder
        raise AttributeError(f"module 'pycares' has no attribute {name!r}")

    current_getattr = getattr(pycares, "__getattr__", None)

    if current_getattr is None:
        pycares.__getattr__ = _compat_getattr
        return

    def _combined_getattr(name: str):
        if name.startswith("ares_") and name.endswith("_result"):
            placeholder = type(name, (), {})
            setattr(pycares, name, placeholder)
            return placeholder
        return current_getattr(name)

    pycares.__getattr__ = _combined_getattr


_ensure_stub_notifications()
_ensure_pycares_compat()

from homeassistant import loader
from homeassistant.components.automation.config import PLATFORM_SCHEMA
from homeassistant.components.blueprint.errors import BlueprintException
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.const import CONF_ACTIONS, CONF_CONDITIONS, CONF_TRIGGERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import frame, script
from homeassistant.helpers.condition import async_validate_conditions_config
from homeassistant.helpers.trigger import async_validate_trigger_config

try:
    from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
except ImportError:  # pragma: no cover - older HA may lack schemas module
    BLUEPRINT_SCHEMA = None

from homeassistant.util import yaml as yaml_util

_SUPPORTS_SCHEMA = any(
    param.kind == inspect.Parameter.KEYWORD_ONLY and param.name == "schema"
    for param in inspect.signature(Blueprint.__init__).parameters.values()
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_VALIDATION_INPUTS_PATH = _REPOSITORY_ROOT / "tests" / "blueprint_inputs.yaml"


def _load_validation_inputs() -> dict[str, dict[str, object]]:
    """Load representative inputs used to expand each blueprint."""
    data = yaml_util.load_yaml(_VALIDATION_INPUTS_PATH)
    if not isinstance(data, dict):
        raise TypeError(
            f"Validation inputs must be a mapping: {_VALIDATION_INPUTS_PATH}"
        )
    return data


def _fixture_key(path: Path) -> str:
    """Return a stable repository-relative fixture key for a blueprint path."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(_REPOSITORY_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


async def validate_one(
    hass: HomeAssistant,
    path: Path,
    validation_inputs: dict[str, dict[str, object]],
) -> bool:
    """Validate a blueprint and a representative expanded automation."""
    try:
        # Parse YAML (supports Home Assistant tags like !input)
        data = yaml_util.load_yaml(path)
        # Validate against the official blueprint schema
        kwargs: dict[str, object] = {"path": str(path)}
        if _SUPPORTS_SCHEMA and BLUEPRINT_SCHEMA is not None:
            kwargs["schema"] = BLUEPRINT_SCHEMA
        blueprint = Blueprint(data, **kwargs)

        key = _fixture_key(path)
        if key not in validation_inputs:
            raise ValueError(
                f"Missing representative inputs for {key} in {_VALIDATION_INPUTS_PATH}"
            )

        blueprint_inputs = BlueprintInputs(
            blueprint,
            {
                "id": f"validation_{path.stem}",
                "alias": f"Validation fixture for {path.name}",
                "use_blueprint": {
                    "path": key,
                    "input": validation_inputs[key],
                },
            },
        )
        blueprint_inputs.validate()
        expanded_automation = blueprint_inputs.async_substitute()
        validated_automation = PLATFORM_SCHEMA(expanded_automation)
        await async_validate_trigger_config(hass, validated_automation[CONF_TRIGGERS])
        if CONF_CONDITIONS in validated_automation:
            await async_validate_conditions_config(
                hass, validated_automation[CONF_CONDITIONS]
            )
        await script.async_validate_actions_config(
            hass, validated_automation[CONF_ACTIONS]
        )

        print(f"✅ {path} — blueprint and expanded automation valid")
        return True
    except BlueprintException as err:
        print(f"❌ {path}\n    {err}", file=sys.stderr)
        return False
    except Exception as err:  # noqa: BLE001  # pylint: disable=broad-except
        print(f"❌ {path}\n    {err}", file=sys.stderr)
        return False


async def main(paths):
    # Static automation schema validation uses Home Assistant's frame helper for
    # deprecation reporting, so provide the minimal core context it expects.
    hass = HomeAssistant(str(_REPOSITORY_ROOT))
    loader.async_setup(hass)
    frame.async_setup(hass)

    try:
        validation_inputs = _load_validation_inputs()
    except Exception as err:  # noqa: BLE001  # pylint: disable=broad-except
        print(f"❌ {_VALIDATION_INPUTS_PATH}\n    {err}", file=sys.stderr)
        sys.exit(1)

    ok = True
    for p in paths:
        if not await validate_one(hass, Path(p), validation_inputs):
            ok = False
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No blueprint files given", file=sys.stderr)
        sys.exit(2)
    asyncio.run(main(sys.argv[1:]))
