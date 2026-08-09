"""Regression checks for the climate change classifier blueprint."""

import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER_PATH = (
    REPOSITORY_ROOT / "blueprints" / "automation" / "climate_change_classifier.yaml"
)
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "blueprint-validation.yaml"
INPUTS_PATH = REPOSITORY_ROOT / "tests" / "blueprint_inputs.yaml"
SCHEDULE_PATH = (
    REPOSITORY_ROOT / "blueprints" / "automation" / "multi_zone_climate.yaml"
)


class ClimateChangeClassifierRegressionTests(unittest.TestCase):
    """Protect the classifier behavior that previously regressed."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.classifier = CLASSIFIER_PATH.read_text(encoding="utf-8")
        cls.schedule = SCHEDULE_PATH.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.inputs = INPUTS_PATH.read_text(encoding="utf-8")

    def test_guard_is_driven_by_monitored_control_calls(self) -> None:
        """Periodic automation runs must not continuously hold the guard."""
        self.assertNotIn("automation_triggered", self.classifier)
        self.assertNotIn("schedule_recent_window_seconds", self.classifier)
        self.assertNotIn("schedule_automations", self.classifier)
        self.assertIn(
            "Automation or script called a monitored climate or damper service",
            self.classifier,
        )

    def test_service_targets_cover_home_assistant_selectors(self) -> None:
        """Indirect service targets must resolve to their member entities."""
        service_targets = self.classifier.split("service_targets: |-", maxsplit=1)[
            1
        ].split("service_hits_monitored_entity:", maxsplit=1)[0]
        for helper in (
            "expand(entity)",
            "device_entities(device)",
            "area_entities(area)",
            "floor_entities(floor)",
            "label_entities(label)",
            "label_devices(label)",
            "label_areas(label)",
        ):
            with self.subTest(helper=helper):
                self.assertIn(helper, service_targets)
        self.assertNotIn("d.get('target')", service_targets)

    def test_direct_service_targets_use_the_fast_path(self) -> None:
        """Direct entity IDs must not be expanded through the state registry."""
        service_targets = self.classifier.split("service_targets: |-", maxsplit=1)[
            1
        ].split("service_hits_monitored_entity:", maxsplit=1)[0]
        self.assertIn("entity.startswith('group.')", service_targets)
        self.assertNotIn("expand(entity_ids)", service_targets)
        self.assertIn("max: 50", self.classifier)

    def test_service_hits_respect_the_called_domain(self) -> None:
        """Indirect targets from another domain must not open the guard."""
        service_hits = self.classifier.split(
            "service_hits_monitored_entity: |-", maxsplit=1
        )[1].split("schedule_guard_timer_event_matches:", maxsplit=1)[0]
        self.assertIn("entity.split('.')[0]", service_hits)
        self.assertIn("entity_domain == service_domain", service_hits)
        self.assertIn("service_domain == 'homeassistant'", service_hits)

    def test_time_triggered_schedule_marks_real_control_calls(self) -> None:
        """Root-context schedule writes must open the guard without run guards."""
        marker = "multi_zone_climate_scheduled_control"
        self.assertIn(f"event_type: {marker}", self.classifier)
        self.assertIn(
            "Companion schedule announced a monitored control call", self.classifier
        )
        self.assertEqual(self.schedule.count(f"event: {marker}"), 7)
        self.assertEqual(
            self.schedule.count(f"event: {marker}"),
            self.schedule.count("action: climate.")
            + self.schedule.count("action: switch."),
        )

    def test_manual_override_waits_for_a_state_change(self) -> None:
        """A failed or no-op command must not enable manual override."""
        self.assertNotIn("homekit_state_change", self.classifier)
        self.assertNotIn("trigger.event.context.user_id is not none", self.classifier)
        self.assertIn(
            "State change clearly initiated by a HA user context", self.classifier
        )

    def test_settle_conditions_query_live_state(self) -> None:
        """The post-delay conditions must not reuse pre-delay booleans."""
        settle_sequence = self.classifier.split(
            "- alias: Recheck the live schedule guard after settling", maxsplit=1
        )[1]
        self.assertIn("is_state(schedule_guard_flag_entity, 'on')", settle_sequence)
        self.assertIn("state_attr(trigger.entity_id, 'temperature')", settle_sequence)
        self.assertNotIn("state_change_still_matches_after_settle", self.classifier)

    def test_guard_is_reconciled_across_lifecycle_events(self) -> None:
        """Lifecycle events must keep the guard aligned with the live timer."""
        for event_type in ("timer.finished", "timer.cancelled", "timer.paused"):
            with self.subTest(event_type=event_type):
                self.assertIn(f"event_type: {event_type}", self.classifier)
        self.assertIn("id: schedule_guard_idle", self.classifier)
        self.assertIn("id: homeassistant_started", self.classifier)
        self.assertIn("event_type: automation_reloaded", self.classifier)
        self.assertIn(
            "and is_state(schedule_guard_timer_entity, 'active')", self.classifier
        )
        stopped_guard = self.classifier.split(
            "- alias: Schedule guard timer stopped", maxsplit=1
        )[1].split(
            "- alias: Reconcile the guard after Home Assistant or automations restart",
            maxsplit=1,
        )[0]
        self.assertIn(
            "and not is_state(schedule_guard_timer_entity, 'active')",
            stopped_guard,
        )
        reconciliation = self.classifier.split(
            "- alias: Reconcile the guard after Home Assistant or automations restart",
            maxsplit=1,
        )[1].split(
            "- alias: Companion schedule announced a monitored control call",
            maxsplit=1,
        )[0]
        self.assertIn("is_state(schedule_guard_timer_entity, 'active')", reconciliation)
        self.assertIn("action: input_boolean.turn_on", reconciliation)
        self.assertIn("action: input_boolean.turn_off", reconciliation)

    def test_ci_validates_all_blueprints_without_multiline_outputs(self) -> None:
        """Multi-file blueprint changes must not corrupt a step output."""
        self.assertNotIn("GITHUB_OUTPUT", self.workflow)
        self.assertIn("BLUEPRINT_FILES", self.workflow)
        self.assertIn("python -m unittest discover", self.workflow)

    def test_schedule_gates_expensive_zone_evaluation(self) -> None:
        """Inactive windows must stop before sensor expansion and zone scoring."""
        gate = self.schedule.index(
            "alias: Skip inactive windows and manual overrides before expensive evaluation"
        )
        heavy_evaluation = self.schedule.index("zone_model: >-")
        self.assertLess(gate, heavy_evaluation)
        self.assertIn("effective_trigger_delay", self.schedule[gate:heavy_evaluation])

    def test_schedule_recalculates_on_events_with_a_watchdog(self) -> None:
        """Selected state changes should drive normal runs; polling is fallback."""
        self.assertIn("id: control_state", self.schedule)
        self.assertIn("id: presence_state", self.schedule)
        self.assertIn("id: recalculation_state", self.schedule)
        self.assertIn("value: 30m", self.schedule)
        self.assertIn("default: 1m", self.schedule)

    def test_presence_changes_ignore_attribute_only_updates(self) -> None:
        """GPS attribute refreshes must not occupy the single schedule runner."""
        presence_trigger = self.schedule.split("id: presence_state", maxsplit=1)[
            1
        ].split("id: recalculation_state", maxsplit=1)[0]
        self.assertIn("to: null", presence_trigger)

    def test_existing_schedule_three_inputs_remain_a_validation_fixture(self) -> None:
        """The user's legacy automation shape must stay covered by HA validation."""
        self.assertIn(
            "temperature_sync_script: script.validation_legacy_temperature_sync",
            self.inputs,
        )
        self.assertIn("update_interval: 15m", self.inputs)
        self.assertIn("temp_sensors: sensor.validation_living_temperature", self.inputs)

    def test_zone_scoring_is_consolidated_into_one_pass(self) -> None:
        """Zone readings, mode maxima, and validity should be computed together."""
        zone_model = self.schedule.split("zone_model: >-", maxsplit=1)[1].split(
            "zone_data: \"{{ zone_model.zones }}\"", maxsplit=1
        )[0]
        self.assertIn("heat_max=0", zone_model)
        self.assertIn("has_valid_temp=false", zone_model)
        self.assertNotIn("sort(attribute='urgency'", zone_model)
        self.assertNotIn("map(attribute='heat')", self.schedule)

    def test_zone_writes_are_batched_and_only_changed_dampers_are_staggered(self) -> None:
        """No-op entities should not add service calls or artificial delays."""
        self.assertIn("batched_extra_temp_targets", self.schedule)
        self.assertIn(
            'entity_id: "{{ batched_extra_temp_targets }}"', self.schedule
        )
        self.assertEqual(
            self.schedule.count('for_each: "{{ damper_updates }}"'), 2
        )
        self.assertNotIn('for_each: "{{ zone_data_for_mode }}"', self.schedule)

    def test_heat_and_cool_zone_offsets_are_independent(self) -> None:
        """Narrow-range zone climates need distinct heat and cool targets."""
        self.assertIn("zone_cool_temperature_offset:", self.schedule)
        self.assertIn("zone_heat_temp_offset | float(0)", self.schedule)
        self.assertIn("zone_cool_temp_offset | float(0)", self.schedule)
        self.assertIn("zone_cool_temperature_offset: 3", self.inputs)

    def test_zone_threshold_overrides_accept_helper_entities(self) -> None:
        """Per-zone dashboard helpers must resolve to their current states."""
        for override, fallback in (
            ("z_low_raw", "low"),
            ("z_high_raw", "high"),
            ("z_dry_raw", "dry_t"),
            ("z_hum_raw", "hum_h"),
        ):
            with self.subTest(override=override):
                self.assertIn(f"states({override})", self.schedule)
                self.assertIn(f"default=({fallback} | float)", self.schedule)
        self.assertIn(
            "low_temp: input_number.validation_main_heat_threshold", self.inputs
        )
        self.assertIn(
            "high_temp: input_number.validation_bedrooms_cool_threshold", self.inputs
        )


if __name__ == "__main__":
    unittest.main()
