"""Execute the actual zone-write loop with Home Assistant's script engine."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from scripts.ha_blueprint_validate import frame, loader, script, yaml_util
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.template import Template


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
        blueprint = yaml_util.parse_yaml(source)
        self.target_selection = next(
            action['variables']['extra_temp_targets_to_update']
            for action in blueprint['actions']
            if 'extra_temp_targets_to_update' in action.get('variables', {})
        )
        loop = find_zone_loop(blueprint)
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
            self.hass.states.async_set(zone, 'heat', {
                'temperature': 18, 'supported_features': 1,
                'min_temp': 16, 'max_temp': 30, 'target_temp_step': 1,
            })

        async def set_temperature(call):
            targets = call.data['entity_id']
            self.assertEqual(len(targets), 1)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            await asyncio.sleep(0)
            self.calls.extend(targets)
            state = self.hass.states.get(targets[0])
            self.hass.states.async_set(targets[0], state.state, {
                **state.attributes, 'temperature': call.data['temperature'],
            })
            self.active -= 1
            self.after_call()

        self.hass.services.async_register('climate', 'set_temperature', set_temperature)

    def update_zone(self, entity, **attributes):
        state = self.hass.states.get(entity)
        self.hass.states.async_set(entity, state.state, {
            **state.attributes, **attributes,
        })

    async def run_loop(self, target=22, mode='heat'):
        await self.runner.async_run({
            'ready_extra_temp_targets_to_update': [
                'climate.one', 'climate.two', 'climate.three'
            ],
            'head_entity': 'climate.head', 'mode': mode, 'zone_set_temp': target,
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

    async def test_range_changed_before_loop_skips_invalid_target(self):
        self.update_zone('climate.one', min_temp=23, max_temp=27)
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.two', 'climate.three'])

    async def test_range_is_rechecked_between_writes(self):
        self.after_call = lambda: self.update_zone(
            'climate.two', min_temp=23, max_temp=27
        )
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.one', 'climate.three'])

    async def test_above_maximum_is_skipped(self):
        self.update_zone('climate.one', max_temp=21)
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.two', 'climate.three'])

    async def test_range_boundaries_are_accepted_in_both_modes(self):
        for mode in ['heat', 'cool']:
            for target in [23, 27]:
                with self.subTest(mode=mode, target=target):
                    self.calls.clear()
                    self.hass.states.async_set('climate.head', mode)
                    for zone in ['climate.one', 'climate.two', 'climate.three']:
                        self.hass.states.async_set(zone, mode, {
                            'temperature': 25, 'supported_features': 1,
                            'min_temp': 23, 'max_temp': 27, 'target_temp_step': 1,
                        })
                    await self.run_loop(target=target, mode=mode)
                    self.assertEqual(
                        self.calls, ['climate.one', 'climate.two', 'climate.three']
                    )

    async def test_step_is_rechecked_before_write(self):
        self.update_zone('climate.one', target_temp_step=1)
        self.update_zone('climate.two', target_temp_step=0.5)
        self.update_zone('climate.three', target_temp_step=0)
        await self.run_loop(target=22.5)
        self.assertEqual(self.calls, ['climate.two', 'climate.three'])

    async def test_lost_temperature_support_is_skipped(self):
        self.after_call = lambda: self.update_zone(
            'climate.two', supported_features=2
        )
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.one', 'climate.three'])

    async def test_cooling_target_below_live_range_is_skipped(self):
        self.hass.states.async_set('climate.head', 'cool')
        self.hass.states.async_set('climate.one', 'cool', {
            'temperature': 25, 'supported_features': 1,
            'min_temp': 23, 'max_temp': 27, 'target_temp_step': 1,
        })
        await self.run_loop(mode='cool')
        self.assertEqual(self.calls, [])

    async def test_candidates_are_not_excluded_by_old_range_or_step(self):
        self.update_zone('climate.one', min_temp=23, max_temp=27)
        self.update_zone('climate.two', max_temp=21)
        self.update_zone('climate.three', target_temp_step=3)
        selected = Template(self.target_selection, self.hass).async_render({
            'mode': 'heat', 'zone_set_temp': 22,
            'extra_temp_targets': ['climate.one', 'climate.two', 'climate.three'],
        })
        self.assertEqual(selected, ['climate.one', 'climate.two', 'climate.three'])
        for zone in selected:
            self.update_zone(zone, min_temp=20, max_temp=24, target_temp_step=1)
        await self.run_loop()
        self.assertEqual(self.calls, selected)

    async def test_timeout_and_next_run_retry_outstanding_zones(self):
        def fail_once():
            self.after_call = lambda: None
            raise TimeoutError

        self.after_call = fail_once
        with self.assertLogs(level='ERROR'):
            try:
                await self.run_loop()
            except TimeoutError:
                # Older HA versions propagate raw controller timeouts despite
                # continue_on_error; newer versions continue to later zones.
                self.assertEqual(self.calls, ['climate.one'])
        await self.run_loop()
        self.assertEqual(self.calls, ['climate.one', 'climate.two', 'climate.three'])
