# LuxPower Modbus Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/ant0nkr/luxpower-modbus-hacs?style=for-the-badge)](https://github.com/ant0nkr/luxpower-modbus-hacs/releases)
[![GitHub License](https://img.shields.io/github/license/ant0nkr/luxpower-modbus-hacs?style=for-the-badge)](https://github.com/ant0nkr/luxpower-modbus-hacs/blob/main/LICENSE)

A comprehensive Home Assistant integration to monitor and control LuxPower inverters via their Modbus TCP interface.

This integration connects directly to your inverter's WiFi dongle, providing real-time data and control over various settings without relying on the cloud.

## Features

* **Real-time Monitoring:** Track PV power, battery state of charge (SOC), grid import/export, load consumption, and more.
* **Inverter Control:** Change charge/discharge currents, set timed charging/discharging periods, and enable/disable features like grid feed-in.
* **Detailed States:** A user-friendly text sensor shows exactly what the inverter is doing (e.g., "PV Powering Load & Charging Battery").
* **Calculated Sensors:** Includes derived sensors like "Load Percentage" for a clearer view of your system's performance.
* **Local Polling:** All communication is local. No cloud dependency.

### Prerequisites

Your LuxPower inverter's WiFi data logging dongle must be connected to the same local network as your Home Assistant instance. You will need to know its IP address.

### HACS (Home Assistant Community Store)

This integration needs to be added to HACS as a **custom repository**.

1.  Navigate to **HACS** > **Integrations** in your Home Assistant instance.
2.  Click the three-dots menu in the top-right corner and select **"Custom repositories"**.
3.  In the dialog box, paste your GitHub repository URL into the "Repository" field:
    `https://github.com/ant0nkr/luxpower-modbus-hacs`
4.  In the "Category" dropdown, select **"Integration"**.
5.  Click the **"ADD"** button.
6.  The repository will now appear in your HACS list. Click on it and then click the **"DOWNLOAD"** button.
7.  Restart Home Assistant when prompted.

### Manual Installation

1.  Copy the `lxp_modbus` folder from this repository into your Home Assistant `custom_components` directory.
2.  Restart Home Assistant.

## Configuration

Configuration is done entirely through the Home Assistant UI.

1.  Go to **Settings** > **Devices & Services**.
2.  Click **Add Integration** and search for **"Luxpower Inverter (Modbus)"**.
3.  Fill in the required details for your inverter.

### Configuration Options

| Name                   | Type    | Description                                                                              |
| ---------------------- | ------- | ---------------------------------------------------------------------------------------- |
| **IP Address** | string  | **(Required)** The IP address of your inverter's WiFi dongle.                              |
| **Port** | integer | **(Required)** The communication port for the Modbus connection, typically `8000`.           |
| **Dongle Serial Number**| string  | **(Required)** The 10-character serial number of your WiFi dongle.                         |
| **Inverter Serial Number**| string  | **(Required)** The 10-character serial number of your inverter.                            |
| **Polling Interval** | integer | **(Required)** How often (in seconds) to poll the inverter for data. Default is 10.        |
| **Inverter Rated Power**| integer | **(Required)** The rated power of your inverter in Watts (e.g., `5000` for a 5kW model).   |
| **Entity Prefix** | string  | (Optional) A custom prefix for all entity names (e.g., 'LXP'). Leave blank for no prefix. |

## Entities

This integration creates a wide range of entities to give you full visibility and control over your inverter.

#### Sensors
Provides detailed operational data, including:
* Inverter State (Text and Code)
* Battery SOC & SOH
* PV Power (Total and per-string)
* Grid Import/Export Power
* Load Power
* Battery Charge/Discharge Power
* Daily & Total Energy Statistics (PV, Grid, Load, etc.)
* Temperatures (Battery, Radiator, etc.)
* Voltages, Currents, and Frequencies for Grid, EPS, and Battery.
* Calculated Load Percentage

#### Numbers
Allows control over inverter settings:
* Charge & Discharge Currents
* AC Charge Power Limit
* End of Discharge (EOD) SOC
* Battery Stop Charging Voltage/SOC

#### Switches
Enable or disable key features on the fly:
* AC Charging Enable
* Feed-In Grid Enable
* Forced Discharge Enable
* Eco & Green Modes

#### Selects
Choose from predefined operational modes:
* AC Charge Type (by Time, SOC, etc.)
* Output Priority (Battery first, PV first, etc.)

#### Time
Set schedules for timed operations:
* AC Charging Start & End Times
* Peak Shaving Start & End Times

## Blueprints

This integration includes blueprints to help you get started with powerful automations.

### How to Import Blueprints

There are two ways to get the blueprints into your Home Assistant instance.

**Method 1: Direct Import Button (Easiest)**

Click the "Import Blueprint" button under the blueprint you wish to use. This will take you to your Home Assistant instance to complete the import.

**Method 2: Manual Import**

1.  In Home Assistant, go to **Settings** > **Automations & Scenes**.
2.  Select the **Blueprints** tab.
3.  Click the **Import Blueprint** button in the bottom right.
4.  Paste the "Manual Import URL" for the blueprint you want.
5.  Click **"Preview Blueprint"** and then **"Import Blueprint"**.

---

### Available Blueprints

#### Force Charge for a Specific Duration
This script blueprint allows you to temporarily force the inverter to charge from the grid for a set amount of time. It saves your existing settings, applies the temporary charge schedule, and restores your settings when finished.

[![Open your Home Assistant instance and import this blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fant0nkr%2Fluxpower-modbus-hacs%2Fmain%2Fblueprints%2Fscript%2Flxp_force_charge.yaml)
> Manual Import URL: `https://raw.githubusercontent.com/ant0nkr/luxpower-modbus-hacs/main/blueprints/script/lxp_force_charge.yaml`

## Debugging

If you are having issues, you can enable debug logging by adding the following to your `configuration.yaml` file:

```yaml
logger:
  default: info
  logs:
    custom_components.lxp_modbus: debug
