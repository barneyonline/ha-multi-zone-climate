"""Execute the actual zone-write loop with Home Assistant's script engine."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from scripts.ha_blueprint_validate import frame, loader, script, yaml_util
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv


ROOT = Path(__file__).resolve().parents[1]


def find_zone_loop(node):
    """Find the zone loop without depending on surrounding action positions."""
    if isinstance(node, dict):
        if node.get('repeat', {}).get('for_each') == (
            '{{ ready_extra_temp_targets_to_update }}'
        ):
            return node
        for value in node.values():
            if found := find_zone_loop(value):
                return found
    elif isinstance(node, list):
        for value in node:
            if found := find_zone_loop(value):
                return found
    return None


class ZoneTemperatureRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.hass = HomeAssistant(self.directory.name)
        loader.async_setup(self.hass)
        frame.async_setup(self.hass)
        source = (ROOT / 'blueprints/automation/multi_zone_climate.yaml').read_text()
        # Only this input is used by the extracted sequence.
        source = source.replace('!input manual_override', 'input_boolean.override')
        loop = find_zone_loop(yaml_util.parse_yaml(source))
        self.assertIsNotNone(loop)
        self.runner = script.Script(
            self.hass, cv.SCRIPT_SCHEMA([loop]), 'zone regression', 'automation'
        )
        self.calls = []
        self.active = 0
        self.max_active = 0
        self.after_call = lambda: None
        self.hass.states.async_set('input_boolean.override', 'off')
        self.hass.states.async_set('climate.head', 'heat')
        for zone in ['climate.one', 'climate.two', 'climate.three']:
            self.hass.states.async_set(zone, 'heat', {'temperature': 18})

        async def set_temperature(call):
            targets = call.data['entity_id']
            self.assertEqual(len(targets), 1)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            await asyncio.sleep(0)
            self.calls.extend(targets)
            self.hass.states.async_set(targets[0], 'heat', {'temperature': 22})
            self.active -= 1
            self.after_call()

        self.hass.services.async_register('climate', 'set_temperature', set_temperature)

    async def run_loop(self):
        await self.runner.async_run({
            'ready_extra_temp_targets_to_update': [
                'climate.one', 'climate.two', 'climate.three'
            ],
            'head_entity': 'climate.head', 'mode': 'heat', 'zone_set_temp': 22,
        }, context=Context())
        await self.hass.async_block_till_done()

    async def test_writes_are_awaited_one_entity_at_a_time(self):
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.one', 'climate.two', 'climate.three'])
        self.assertEqual(self.max_active, 1)

    async def test_manual_override_stops_remaining_writes(self):
        self.after_call = lambda: self.hass.states.async_set('input_boolean.override', 'on')
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.one'])

    async def test_head_mode_change_stops_remaining_writes(self):
        self.after_call = lambda: self.hass.states.async_set('climate.head', 'cool')
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.one'])

    async def test_noop_zone_is_skipped_without_skipping_later_zone(self):
        self.after_call = lambda: self.hass.states.async_set(
            'climate.two', 'heat', {'temperature': 22}
        )
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.one', 'climate.three'])

    async def test_unavailable_zone_is_skipped(self):
        self.after_call = lambda: self.hass.states.async_set('climate.two', 'unavailable')
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.one', 'climate.three'])

    async def test_timeout_aborts_and_next_run_retries_outstanding_zones(self):
        def fail_once():
            self.after_call = lambda: None
            raise TimeoutError

        self.after_call = fail_once
        with self.assertLogs(level='ERROR'):
            with self.assertRaises(TimeoutError):
                await self.run_loop()
        self.assertEqual(self.calls, ['climate.one'])
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.one', 'climate.two', 'climate.three'])
