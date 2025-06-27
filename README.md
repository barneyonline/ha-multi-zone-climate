# Dynamic Multi-Zone Climate Schedule

This repository provides a Home Assistant blueprint that coordinates a single HVAC head-unit across multiple zones. It selects a global heating, cooling or drying mode based on the most urgent zone and then staggers damper control for each zone.

## Importing the Blueprint

1. In Home Assistant, navigate to **Settings → Automations & Scenes → Blueprints**.
2. Click **Import Blueprint** and paste the following URL:
   ```
   https://raw.githubusercontent.com/USER/REPO/main/blueprints/automation/multi_zone_climate.yaml
   ```
   Replace `USER` and `REPO` with this repository's owner and name if different.
3. Confirm the import.

## Configuration

When creating an automation from the blueprint you will need to provide:

- **Schedule Start/End Times** – the daily window during which the system operates.
- **Climate Head-Unit** – the shared climate entity to control.
- **Temperature & Humidity Thresholds** – values that trigger heating, cooling or dry mode.
- **Zone Configuration** – for each zone specify its temperature sensor, humidity sensor and damper switch.
- Optional booleans allow enabling/disabling the schedule and pausing it with a manual override.

Once configured, the automation will automatically set the head-unit's mode and temperature and toggle individual dampers based on zone urgency.
