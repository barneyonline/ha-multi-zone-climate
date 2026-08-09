# Dynamic Multi-Zone Climate Schedule

Home Assistant blueprints for coordinating one HVAC head unit across multiple
zones and distinguishing scheduled changes from manual climate control.

## Import

### Multi-zone schedule

[![Import the schedule blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fbarneyonline%2Fha-multi-zone-climate%2Fmain%2Fblueprints%2Fautomation%2Fmulti_zone_climate.yaml)

The schedule selects heating, cooling, or dry mode from zone demand, controls
dampers, respects occupancy and manual override, and shuts down safely when its
active window has no demand.

### Climate change classifier

[![Import the classifier blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fbarneyonline%2Fha-multi-zone-climate%2Fmain%2Fblueprints%2Fautomation%2Fclimate_change_classifier.yaml)

Use the classifier with the schedule's manual-override helper. It watches the
head unit, zone climate entities, and dampers. Schedule markers and a dedicated
guard `input_boolean` and `timer` prevent scheduled writes from being mistaken
for UI, HomeKit, or physical-device changes.

## Setup

Create an automation from the schedule blueprint and select:

- Schedule times/days, occupancy entities, enable flag, and manual override.
- The head-unit climate entity and temperature/humidity setpoint helpers.
- Up to eight zones, each with a damper, sensors, and optional enable flag or
  threshold overrides.
- Optional zone climate entities for direct temperature synchronization.

Zone climate targets use independent offsets: `head target + heat offset` in
heat mode and `head target - cool offset` in cool mode. Targets outside an
entity's advertised range are skipped. Increase the zone settle delay if the
controller needs extra time after a mode or head-unit setpoint change.

```yaml
zones:
  - name: Living Room
    damper_switch: switch.living_room_damper
    enabled_flag: input_boolean.living_room_enabled
    temp_sensors: sensor.living_room_temperature
    humidity_sensors: sensor.living_room_humidity
  - name: Bedrooms
    damper_switch: switch.bedrooms_damper
    temp_sensors:
      - sensor.bedroom_one_temperature
      - sensor.bedroom_two_temperature
```

The watchdog interval is a fallback. Add recalculation entities only when you
want selected sensors or helpers to trigger immediate runs. Person triggers
react only to actual home/away state changes, not GPS attribute updates.

The blueprint runs in `single` mode to avoid overlapping commands to slow HVAC
controllers. It skips no-op writes and can use an availability entity to avoid
damper calls while the controller is offline.

## Existing automations

Existing schedule inputs remain compatible. The old
`temperature_sync_script` input is ignored and can be removed; zone temperature
synchronization is built into the blueprint.

After updating an imported blueprint, reload automations in Home Assistant.

## Troubleshooting

- AirBase `get_zone_setting` or `set_zone_setting` timeouts indicate a controller
  or network problem. Configure a controller availability entity and avoid a
  watchdog interval shorter than a worst-case automation run.
- If a zone rejects a temperature update, check its current min/max range and
  increase the zone settle delay.
- Use the automation trace to confirm which trigger and condition stopped a run.
