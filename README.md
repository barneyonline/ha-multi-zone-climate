# Dynamic Multi‑Zone Climate Schedule (2025‑06)

This repository provides a Home Assistant blueprint that coordinates a single HVAC head-unit across multiple zones. It selects a global heating, cooling or drying mode based on the most urgent zone, staggers damper changes for each zone, and explicitly shuts the system down when the schedule ends, nobody is home, or the automation is disabled.

## Importing the Blueprint

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fbarneyonline%2Fha-multi-zone-climate%2Fmain%2Fblueprints%2Fautomation%2Fmulti_zone_climate.yaml)

Works with current Home Assistant releases. No bleeding‑edge features are
required; if you previously saw an import error, update to a recent HA version
and use the raw blueprint URL above.

## Configuration

When creating an automation from the blueprint you will need to provide:

- **Schedule Start/End Times** – the daily window during which the system operates.
- **Active Days** – days of the week when the schedule is enabled.
- **Climate Head-Unit** – the shared climate entity to control.
- **Zone Temperature Climate Entities** – optional additional climate entities (for example per-zone temperature entities) that should track a zone-specific setpoint derived from the head-unit target. In `heat` mode the blueprint sends `head-unit target + offset`; in `cool` mode it sends `head-unit target - offset`. If one of them is not ready for the selected heat/cool mode or cannot accept the computed setpoint, it will be skipped rather than failing the whole automation.
- **Zone Temperature Offset** – the adjustable `+/-` value used when updating the optional zone climate entities. The default is `1°C`, so a heat target of `20°C` becomes `21°C` for zones and a cool target of `23°C` becomes `22°C`.
- **Temperature & Humidity Thresholds** – zone start thresholds for heating, cooling or dry mode. A common setup is `heat setpoint - 1°C` and `cool setpoint + 1°C`.
- **Mode Toggles** – switches to enable or disable heating, cooling or dry mode as well as head-unit and damper control.
- **Zone Configuration** – edit the YAML list of zones to specify each zone's damper switch and one or more temperature and/or humidity sensors. Optional overrides let you adjust thresholds per zone. Up to eight zones are supported.
- **Zone Enable Flags** – optionally provide an `input_boolean` per zone to dynamically enable or disable that zone's damper.
- **Enable/Override Flags** – input_boolean entities used to enable the schedule and to pause active automatic control manually. When the schedule window ends, nobody is home, or the automation is disabled, the blueprint turns the head unit off and closes dampers.
- **Damper Update Delay** – seconds to wait between zone damper changes.
- **Update Interval** – how often the blueprint re-evaluates all zones (`1m`, `5m`, `10m`, `15m`).
- **Hysteresis Values** – optional stop-point buffers. For example, with a cool threshold of `23°C` and cool hysteresis of `0.5°C`, cooling starts at `23°C`, stops at `22.5°C`, then waits until the zone rises back to `23°C`.
- **Zone Overrides** – per-zone thresholds and optional area selection.

### Example Zone Configuration

```yaml
zones:
  - name: Living Room
    area: living_room
    damper_switch: switch.living_room_damper
    enabled_flag: input_boolean.living_room_enabled
    temp_sensors:
      - sensor.living_room_temperature
    humidity_sensors:
      - sensor.living_room_humidity
    low_temp: 18
    dry_temp: 20
    hum_high: 65
  - name: Bedroom
    area: bedroom
    damper_switch: switch.bedroom_damper
    enabled_flag: input_boolean.bedroom_enabled
    temp_sensors:
      - sensor.bedroom_temperature
    humidity_sensors:
      - sensor.bedroom_humidity
    high_temp: 25
```

Once configured, the automation will automatically set the head-unit's mode and temperature and toggle individual dampers based on zone urgency. Heating and cooling thresholds are evaluated as start points, while hysteresis is only used to decide when an already-active zone can stop calling for that mode. When there is no active demand, the blueprint also closes any dampers it previously opened so zone state does not drift stale.

## Troubleshooting

If you see a Home Assistant error like `Connection timeout to host http://<airbase-ip>/skyfi/aircon/set_zone_setting`, the failure is coming from the HVAC controller or the path to it rather than from blueprint templating. On Daikin AirBase systems, each zone switch call is translated by the integration into a request against the controller's `set_zone_setting` endpoint.

The blueprint already avoids no-op damper writes, and individual damper service failures are allowed to continue so one slow zone update does not abort the whole automation run. If the timeout persists, check:

- The controller at the logged IP is reachable and responsive on your LAN.
- The selected damper entities are the intended zone switches for that controller.
- Your `Update Interval` is not shorter than the time needed to work through a full damper sequence, especially when `Damper Update Delay` is high.
- The controller is not busy or temporarily unavailable when many zone changes are requested in a short period.
