# Pyrovigil

[![CI](https://github.com/ha-pyrovigil/ha-pyrovigil/actions/workflows/ci.yml/badge.svg)](https://github.com/ha-pyrovigil/ha-pyrovigil/actions)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant custom integration for monitoring Portuguese wildfires.

Pyrovigil aggregates real-time data from ANEPC (civil protection) and IPMA (weather/fire risk) to give you nearby fire alerts, resource deployment counts, and fire risk levels — directly in Home Assistant.

## Features

- **Active fire monitoring** — detects fires within a configurable radius of your home
- **Resource tracking** — personnel, ground vehicles, and aircraft deployed to nearby fires
- **Fire risk forecast** — daily RCM fire risk level (1-5 scale) for your municipality
- **Weather warnings** — IPMA weather alerts for your district
- **Binary sensors** — `fire_nearby` and `high_fire_risk` for automations (sprinklers, notifications, etc.)
- **Events** — `pyrovigil_fire_detected` fires when a new incident appears within your radius
- **Fully toggleable** — every sensor can be individually enabled/disabled

## Data Sources

| Source | Data | Auth | Update Frequency |
|---|---|---|---|
| [ANEPC ArcGIS](https://services-eu1.arcgis.com/VlrHb7fn5ewYhX6y/arcgis/rest/services/OcorrenciasSite/FeatureServer) | Fire incidents, resources | None | Configurable (default 5 min) |
| [IPMA RCM](https://api.ipma.pt/open-data/forecast/meteorology/rcm/) | Fire risk forecast | None | Hourly |
| [IPMA Warnings](https://api.ipma.pt/open-data/forecast/warnings/) | Weather warnings | None | Every 30 min |

All data sources are free, public Portuguese government APIs. No API keys required.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add the repository URL and select **Integration** as the category
4. Search for "Pyrovigil" and install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/pyrovigil/` to your Home Assistant `custom_components/` directory
2. Restart Home Assistant

## Configuration

### UI (recommended)

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Pyrovigil"
3. Enter your coordinates (pre-filled from your HA home zone), alert radius, and polling interval

### YAML

```yaml
pyrovigil:
  latitude: 38.7223
  longitude: -9.1393
  radius: 25          # km (default: 25)
  scan_interval: 5    # minutes (default: 5)
```

### Options

After setup, click **Configure** on the integration to adjust:

- **Alert radius** (5-100 km)
- **Polling interval** (1-30 minutes)
- **High risk threshold** (RCM level 2-5, default: 4)

## Entities

### Sensors

| Entity | Description | Default |
|---|---|---|
| `sensor.pyrovigil_active_fires` | Number of active fires within radius | Enabled |
| `sensor.pyrovigil_nearest_fire` | Distance (km) to the nearest fire | Enabled |
| `sensor.pyrovigil_fire_risk` | Today's fire risk level (1-5) | Enabled |
| `sensor.pyrovigil_total_personnel` | Total firefighters deployed nearby | Disabled |
| `sensor.pyrovigil_total_ground_vehicles` | Total fire trucks deployed nearby | Disabled |
| `sensor.pyrovigil_total_aircraft` | Total aircraft deployed nearby | Disabled |
| `sensor.pyrovigil_fire_risk_tomorrow` | Tomorrow's fire risk level | Disabled |
| `sensor.pyrovigil_weather_warnings` | Number of active weather warnings | Disabled |

### Binary Sensors

| Entity | ON when | Default |
|---|---|---|
| `binary_sensor.pyrovigil_fire_nearby` | Any fire within radius | Enabled |
| `binary_sensor.pyrovigil_high_fire_risk` | Fire risk >= threshold | Enabled |

### Events

| Event | Fired when | Data |
|---|---|---|
| `pyrovigil_fire_detected` | New fire appears within radius | `fire_id`, `distance_km`, `nature`, `concelho`, `latitude`, `longitude` |

## Quick Start: Fire Notifications (Blueprint)

The fastest way to get notified about nearby fires is the included blueprint. No YAML needed.

1. Copy `blueprints/automation/fire_notification.yaml` into your HA config at
   `config/blueprints/automation/pyrovigil/fire_notification.yaml`
2. Go to **Settings** -> **Automations & Scenes** -> **Blueprints**
3. Click **Pyrovigil Fire Notification**
4. Configure:
   - **Notification service** — `notify.notify` sends to all phones, or pick a specific device
   - **Minimum severity** — filter out small fires (low/moderate/high/extreme)
   - **Maximum distance** — only alert within a tighter radius (0 = use configured radius)
   - **Critical alert** — bypasses Do Not Disturb (recommended only for high/extreme)
5. Save. Done.

The notification includes the fire type, location, distance, severity, and an "Open Map" button that shows the fire on Google Maps.

## Automation Examples

### Notify when a fire is detected nearby

```yaml
automation:
  - alias: "Fire nearby notification"
    trigger:
      - platform: event
        event_type: pyrovigil_fire_detected
    action:
      - service: notify.notify
        data:
          title: "Fire detected!"
          message: >
            A {{ trigger.event.data.nature }} fire was detected
            {{ trigger.event.data.distance_km }} km away
            in {{ trigger.event.data.concelho }}.
            Severity: {{ trigger.event.data.severity }}.
```

### Activate sprinklers when fire is nearby

```yaml
automation:
  - alias: "Activate fire suppression"
    trigger:
      - platform: state
        entity_id: binary_sensor.pyrovigil_fire_nearby
        to: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.garden_sprinklers
```

### Alert on high fire risk days

```yaml
automation:
  - alias: "High fire risk warning"
    trigger:
      - platform: state
        entity_id: binary_sensor.pyrovigil_high_fire_risk
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "High fire risk today"
          message: >
            Fire risk level is {{ states('sensor.pyrovigil_fire_risk') }}/5.
            Take precautions.
```

## Development

```bash
# Clone and setup
git clone https://github.com/ha-pyrovigil/ha-pyrovigil.git
cd ha-pyrovigil
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt

# Run tests
pytest tests/ -v --cov=custom_components/pyrovigil

# Lint
ruff check custom_components/ tests/
ruff format custom_components/ tests/
```

## License

MIT
