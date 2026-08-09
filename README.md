# Dynamic Multi‑Zone Climate Schedule

This repository provides a Home Assistant blueprint that coordinates a single HVAC head-unit across multiple zones. It selects a global heating, cooling or drying mode based on the most urgent zone, staggers damper changes for each zone, and only controls devices while its own schedule window is active. During the active window it shuts the system down when nobody is home, the automation is disabled, or no zone is calling for conditioning.

## Importing the Blueprint

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fbarneyonline%2Fha-multi-zone-climate%2Fmain%2Fblueprints%2Fautomation%2Fmulti_zone_climate.yaml)

Works with current Home Assistant releases. No bleeding‑edge features are
required; if you previously saw an import error, update to a recent HA version
and use the raw blueprint URL above.

### Climate Change Classifier Blueprint

The repository also includes a reusable template for the schedule-vs-manual
change classifier:

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fbarneyonline%2Fha-multi-zone-climate%2Fmain%2Fblueprints%2Fautomation%2Fclimate_change_classifier.yaml)

Use it with the same manual override helper as the schedule blueprint. Select
the climate entities and damper switches to watch, plus dedicated schedule
guard `input_boolean` and `timer` helpers. The classifier opens its guard only
when an automation or script actually calls a monitored climate or damper
service; periodic schedule runs that make no device changes do not suppress
manual-change detection. The companion schedule emits a control marker before
each device write so its time-triggered runs are recognized even though Home
Assistant gives them a root context. UI, HomeKit, and physical-device commands
are only classified after the corresponding entity state has changed. The
classifier permits up to 50 parallel executions so a batch of service calls and
the resulting state changes do not exhaust its run capacity.

## Configuration

When creating an automation from the blueprint you will need to provide:

- **Schedule Start/End Times** – the daily window during which the system operates.
- **Active Days** – days of the week when the schedule is enabled.
- **Climate Head-Unit** – the shared climate entity to control.
- **Zone Temperature Climate Entities** – optional additional climate entities (for example per-zone temperature entities) that should track a zone-specific setpoint derived from the head-unit target. In `heat` mode the blueprint sends `head-unit target + offset`; in `cool` mode it sends `head-unit target - offset`. Entities that are not ready for the selected heat/cool mode, do not advertise target-temperature support, or cannot accept the computed setpoint range are skipped.
- **Zone Heat/Cool Temperature Offsets** – independently adjustable values used when updating optional zone climate entities. The defaults are `1°C`, so a heat target of `20°C` becomes `21°C` and a cool target of `23°C` becomes `22°C`. Separate offsets support zone controllers with a narrower target range than the head unit.
- **Zone Temperature Settle Delay** – seconds to wait after changing the head-unit mode or setpoint before writing optional zone temperature climate entities. The default is `30s`, which gives Daikin-style controllers time to accept zone temperature writes after reporting the new mode.
- **Temperature & Humidity Thresholds** – zone start thresholds for heating, cooling or dry mode. A common setup is `heat setpoint - 1°C` and `cool setpoint + 1°C`.
- **Mode Toggles** – switches to enable or disable heating, cooling or dry mode as well as head-unit and damper control.
- **Damper Controller Availability Entity** – optional reachability entity for the zone controller. For Daikin AirBase, use a ping/connectivity sensor for the AirBase IP so damper writes are skipped while the controller is offline or not responding.
- **Zone Configuration** – edit the YAML list of zones to specify each zone's damper switch and one or more temperature and/or humidity sensors. Optional overrides let you adjust thresholds per zone. Up to eight zones are supported.
- **Zone Enable Flags** – optionally provide an `input_boolean` per zone to dynamically enable or disable that zone's damper.
- **Enable/Override Flags** – input_boolean entities used to enable the schedule and to pause active automatic control manually. Outside the schedule window, or while manual override is on, the blueprint leaves the head unit and dampers alone. During the active window, if nobody is home or the automation is disabled, it turns the head unit off and closes dampers.
- **Damper Update Delay** – seconds to wait between damper writes that are actually required. Dampers already in the desired state are skipped without delaying later writes.
- **Event-Driven Recalculation Entities** – select every zone temperature/humidity sensor, zone enable flag, threshold/setpoint helper, and controller-availability entity that should cause an immediate recalculation. Enable and manual-override helpers, plus selected person entities, are already watched automatically.
- **Watchdog Update Interval** – periodic fallback for missed or unselected changes (`1m`, `5m`, `10m`, `15m`, `30m`). The default remains `1m` so existing automations retain their current response time. Once event-driven entities are configured, a longer interval such as `15m` reduces fallback work.
- **Hysteresis Values** – optional stop-point buffers. For example, with a cool threshold of `23°C` and cool hysteresis of `0.5°C`, cooling starts at `23°C`, stops at `22.5°C`, then waits until the zone rises back to `23°C`.
- **Zone Overrides** – per-zone thresholds and optional area selection.

Existing automations may still contain the retired `temperature_sync_script`
input. Home Assistant accepts that extra input, so those automations continue to
load, but the script is no longer invoked. Configure **Zone Temperature Climate
Entities** instead; the blueprint now performs that synchronization directly.

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

Once configured, the automation will automatically set the head-unit's mode and temperature and toggle individual dampers based on zone urgency. Heating and cooling thresholds are evaluated as start points, while hysteresis is only used to decide when an already-active zone can stop calling for that mode. When there is no active demand, the blueprint also closes any dampers it previously opened so zone state does not drift stale. Compatible per-zone climate entities are updated together in one service call after the controller settle period.

The automation intentionally uses `single` execution mode to avoid overlapping
requests to a slow HVAC controller. Most waits finish as soon as the controller
reports the requested state. The configured upper bound for a state-driven run
is approximately `Trigger Settle Delay + 40s + Zone Temperature Settle Delay +
(changed dampers - 1) × Damper Update Delay`; watchdog runs omit the trigger
delay. If you select a watchdog interval shorter than that bound, a watchdog
tick can be skipped while the previous run finishes. Event-driven state changes
will likewise be handled by the next accepted trigger or the watchdog.

## Troubleshooting

If you see a Home Assistant error like `Connection timeout to host http://<airbase-ip>/skyfi/aircon/get_zone_setting`, the failure is coming from the HVAC controller or the path to it rather than from blueprint templating. On Daikin AirBase systems, each zone switch call is translated by the integration into requests against the controller's `get_zone_setting` and `set_zone_setting` endpoints.

The blueprint avoids no-op damper writes, skips overlapping scheduled runs instead of queueing them behind a slow controller, and can skip damper writes entirely while an optional controller availability entity is not ready. If the timeout persists:

- Add a ping/connectivity sensor for the controller IP and select it as **Damper Controller Availability Entity**.
- The controller at the logged IP is reachable and responsive on your LAN.
- The selected damper entities are the intended zone switches for that controller.
- Your **Watchdog Update Interval** is not shorter than the configured worst-case run time above when every periodic tick must be processed, especially when **Damper Update Delay** is high.
- The controller is not busy or temporarily unavailable when many zone changes are requested in a short period.

If you see `Failed to set zone temperature. The device may not support this operation`, the failing call is the optional **Zone Temperature Climate Entities** sync. On Daikin zone climate entities this message is generic: it can mean the controller rejected that particular zone-temperature write even when the device normally supports zone temperature changes. Check whether the target is within the zone's current min/max range and whether the error appears during mode or head-unit setpoint changes. If it happens shortly after the head unit changes mode, increase **Zone Temperature Settle Delay**.
