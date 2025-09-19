# Dynamic Multi‑Zone Climate Schedule (2025‑06)

This repository provides a Home Assistant blueprint that coordinates a single HVAC head-unit across multiple zones. It selects a global heating, cooling or drying mode based on the most urgent zone and then staggers damper control for each zone.

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
- **Temperature Sync Script** – optional script to run whenever the blueprint updates the head-unit setpoint, handy for systems that nudge setpoints to align zones.
- **Temperature & Humidity Thresholds** – values that trigger heating, cooling or dry mode.
- **Zone Configuration** – edit the YAML list of zones to specify each zone's damper switch and one or more temperature and/or humidity sensors. Optional overrides let you adjust thresholds per zone. Up to eight zones are supported.
- **Enable/Override Flags** – input_boolean entities used to enable the schedule and to pause it manually.
- **Damper Update Delay** – seconds to wait between zone damper changes.
- **Update Interval** – how often the blueprint re-evaluates all zones (15s, 30s, 1m, 5m).
- **Hysteresis Values** – optional buffers before heating, cooling or drying engage.
- **Zone Overrides** – per-zone thresholds and optional area selection.

### Example Zone Configuration

```yaml
zones:
  - name: Living Room
    area: living_room
    damper_switch: switch.living_room_damper
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
    temp_sensors:
      - sensor.bedroom_temperature
    humidity_sensors:
      - sensor.bedroom_humidity
    high_temp: 25
```

Once configured, the automation will automatically set the head-unit's mode and temperature and toggle individual dampers based on zone urgency.
