# Dynamic Multi-Zone Climate Schedule

This repository provides a Home Assistant blueprint that coordinates a single HVAC head-unit across multiple zones. It selects a global heating, cooling or drying mode based on the most urgent zone and then staggers damper control for each zone.

## Importing the Blueprint

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbarneyonline%2Fha-multi-zone-climate%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fmulti_zone_climate.yaml)

## Configuration

When creating an automation from the blueprint you will need to provide:

- **Schedule Start/End Times** – the daily window during which the system operates.
- **Climate Head-Unit** – the shared climate entity to control.
- **Temperature & Humidity Thresholds** – values that trigger heating, cooling or dry mode.
- **Zone Configuration** – for each zone specify its temperature sensor, humidity sensor and damper switch.
- **Enable/Override Flags** – input_boolean entities used to enable the schedule and to pause it manually.
- **Damper Update Delay** – seconds to wait between damper adjustments.

### Example Zone Configuration

```yaml
zones:
  - name: Living Room
    temp_sensor: sensor.living_room_temperature
    humidity_sensor: sensor.living_room_humidity
    damper_switch: switch.living_room_damper
  - name: Bedroom
    temp_sensor: sensor.bedroom_temperature
    humidity_sensor: sensor.bedroom_humidity
    damper_switch: switch.bedroom_damper
```

Once configured, the automation will automatically set the head-unit's mode and temperature and toggle individual dampers based on zone urgency.
