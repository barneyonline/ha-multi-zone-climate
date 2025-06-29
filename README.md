# Dynamic Multi-Zone Climate Schedule

This repository provides a Home Assistant blueprint that coordinates a single HVAC head-unit across multiple zones. It selects a global heating, cooling or drying mode based on the most urgent zone and then staggers damper control for each zone.

## Importing the Blueprint

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbarneyonline%2Fha-multi-zone-climate%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fmulti_zone_climate.yaml)

This blueprint uses object selectors with `multiple` and `properties`. These were
introduced in **Home Assistant 2024.5**. Ensure your instance is running 2024.5
or newer before importing.

## Configuration

When creating an automation from the blueprint you will need to provide:

- **Schedule Start/End Times** – the daily window during which the system operates.
- **Active Days** – days of the week when the schedule is enabled.
- **Climate Head-Unit** – the shared climate entity to control.
- **Temperature & Humidity Thresholds** – values that trigger heating, cooling or dry mode.
- **Zone Configuration** – choose each zone's damper switch then add one or more
  temperature and humidity sensors (up to eight zones).
- **Enable/Override Flags** – input_boolean entities used to enable the schedule and to pause it manually.
- **Damper Update Delay** – seconds to wait between damper adjustments.
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
