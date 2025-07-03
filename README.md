# Home Assistant Integration: __evcc☀️🚘- Solar Charging__ (unofficial)

![ha-logo](https://github.com/marq24/ha-evcc/raw/main/logo-ha.png)&nbsp;&nbsp;![evcc-logo](https://github.com/marq24/ha-evcc/raw/main/logo.png)

I was surprised that looks like that there does not exist a simple Home Assistant integration for the very popular evcc. So before my first EV spawned at my driveway, I want to contribute a very simple & basic integration which allow you to control evcc objects simply via the default HA gui and use sensors and switches in your automations.

__Please note__, _that this Home Assistant integration is not official and not supported by the evcc developers. I am not affiliated with evcc in any way. This integration is based on the evcc API and the evcc API documentation._

[![hacs_badge][hacsbadge]][hacs] [![github][ghsbadge]][ghs] [![BuyMeCoffee][buymecoffeebadge]][buymecoffee] [![PayPal][paypalbadge]][paypal] [![hainstall][hainstallbadge]][hainstall]

## Disclaimer

Please be aware that we are developing this integration to the best of our knowledge and belief, but can't give a guarantee. Therefore, use this integration **at your own risk**.

## Requirements

- A running & configured evcc instance in your network
- A Home Assistant instance that can reach your evcc instance

## Main features

- Supporting all evcc API-POST & DELETE requests (except `POST /api/settings/telemetry/<status>`) to adjust the evcc settings, loadpoints and the corresponding vehicles
  - Loadpoint mode [Off, Solar, Min+Solar, Fast]
  - Phases to use [Auto, 1p, 3p]
  - Assign vehicles to loadpoints
  - Configure min & max charging currents
  - Configure cost limits (€ or CO₂)
  - Adjust home-battery settings
  - Adjust/create Vehicle & Loadpoint charging plan via HA-Services [http://[YOUR-HA-INSTANCE]:8123/developer-tools/service](http://[YOUR-HA-INSTANCE]:8123/developer-tools/service)
  
- Supporting most of the other loadpoint and vehicle data that is available via the API - please let me know, if you miss some data - probably it just slipped through my attention during testing.

### Example Dashboard

Take a look at this sample Dashboard (showing Sensors from one load point):

![sampledashboard](https://github.com/marq24/ha-evcc/raw/main/sample-dashboard.png)

## Installation

### Before you start — there are two 'tiny' requirements!

1.  **You must have installed & configured an evcc instance in your network.** This can be either a stand-alone installation (e.g via Docker) or as a HASS-IO-AddOn. This __AddOn__ is available via the [official evcc hassio-addon repository](https://github.com/evcc-io/hassio-addon).
2.  You **must know the URL** from which your HA-Instance can reach your evcc instance.
    - This is usually the IP address of your evcc server and the port on which the evcc server is running (default is `7070`).
    - If you are using a reverse proxy, you need to know the URL that your HA instance can use to reach your evcc instance.
    - When you are using docker (or docker-compose), you must ensure that the containers can communicate with each other. This means that the network and the port must be configured & exposed correctly. It's not enough that you can reach your evcc instance via a browser — your HA container must be also able to reach it!

### Step I: Install the integration

#### Option 1: via HACS

[![Open your Home Assistant instance and adding repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=marq24&repository=ha-evcc&category=integration)

1. ~~Add a custom **integration** repository to HACS: [https://github.com/marq24/ha-evcc](https://github.com/marq24/ha-evcc)<br/>**Let me repeat**: This is an **HACS _integration_**, not an **HASS-IO _AddOn_**, so you need to have HACS installed, and you need to add this as custom **integration repository** to HACS.~~
2. ~~Once the repository is added,~~ use the search bar and type `evcc☀️🚘- Solar Charging`
3. Use the 3-dots at the right of the list entry (not at the top bar!) to download/install the custom integration — the latest release version is automatically selected. Only select a different version if you have specific reasons.
4. After you press download and the process has completed, you must __Restart Home Assistant__ to install all dependencies
5. Setup the evcc custom integration as described below (see _Step II: Adding or enabling the integration_)

  <!--1. In HACS Store, search for [***marq24/ha-evcc***]-->

#### Option 2: manual steps

1. Using the tool of choice, open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `evcc_intg`.
4. Download _all_ the files from the `custom_components/evcc_intg/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. Setup the evcc custom integration as described below (see _Step II: Adding or enabling the integration_)

### Step II: Adding or enabling the integration

__You must have installed the integration (manually or via HACS before)!__

#### Option 1: My Home Assistant (2021.3+)

Just click the following Button to start the configuration automatically (for the rest see _Option 2: Manually steps by step_):

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=evcc_intg)


#### Option 2: Manually — step by step

Use the following steps for a manual configuration by adding the custom integration using the web interface and follow instruction on screen:

- Go to `Configuration -> Integrations` and add "evcc☀️🚘- Solar Charging" integration

#### Common further steps 

- Provide a unique name for the integration installation (will be used in each sensor entity_id) created by the integration
- Provide the URL of your __evcc web server__ (including the port) — e.g. `http://your-evcc-server-ip:7070`
- [optional] Provide the area where the evcc installation is located

After the integration was added, you can use the 'config' button to adjust your settings, you can additionally modify the update interval

Please note that some of the available sensors are __not__ enabled by default.

## Use evcc with your Home Assistant sensor data

Please see the separate document where you can find examples [how to provide your evcc instance with HA sensor data](https://github.com/marq24/ha-evcc/blob/main/HA_AS_EVCC_SOURCE.md).

## Are you are go-eCharger V3 (or higher) User?

Do you know, that as owners of a go-eCharger (V3+) there is no need to use evcc for solar surplus charging? Even without any additional hardware! Home Assistant and the __go-eCharger APIv2 Connect__ Integration is all you need. Get all details from [https://github.com/marq24/ha-goecharger-api2](https://github.com/marq24/ha-goecharger-api2).



## Accessing your vehicle SOC & Range when the vehicle is not connected to a loadpoint

By default, evcc and this integration focus on vehicles connected to a loadpoint, this implies that data like SOC or range are _only available when the vehicle is actually connected_.

Nevertheless, evcc provides this data in the configuration section (no matter of the connection state). If you want to access your vehicle SOC and range, when the vehicle is not connected to a loadpoint, you can do this by adding a command_line sensor to your Home Assistant configuration.yaml file.

> [!IMPORTANT]
> You need to know the technical `vehicle_id`. Depending on from your configuration this is either the value you have specified in the `evcc.yaml` file or it had been automatically generated.
>
> In any case you can request: `http://[YOUR_EVCC_IP]:7070/api/config/devices/vehicle` and check the value of the `name` attribute to get your `vehicle_id`.

> [!NOTE]
> You must authorize your request(s) with the evcc password.
> 

### Command-Line in your HA configuration.yaml

requesting `http://[YOUR_EVCC_IP]:7070/api/config/devices/vehicle/[YOUR_VEHICLE_ID]/status` will return a JSON like this one here

```json
{
  "result": {
    "capacity": {
      "value": 84.68,
      "error": ""
    },
    "chargeStatus": {
      "value": "B",
      "error": ""
    },
    "range": {
      "value": 167,
      "error": ""
    },
    "soc": {
      "value": 39.5,
      "error": ""
    }
  }
}
```

Check if you have already a `command_line` section in your `configuration.yaml` file - if there is none - create one on as top level entry like this (the line '  - sensor: ...' must (obviously) be replaced with the complete sections shown further below):

```yaml
command_line:
  - sensor: ...
```

Add in the `command_line` section of your `configuration.yaml` file the following content: sections with `[CHANGE_ME:xxx]` have to be modified to your requirements. E.g., assuming your assuming `vehicle_id` is __ford_mach_e__, then you have to replace `[CHANGE_ME:YourVehicleId]` with just `ford_mach_e`

```yaml
  - sensor:
      name: '[CHANGE_ME:Your Vehicle SOC & Range]'
      unique_id: [CHANGE_ME:evcc_vehicle_soc_and_range]
      command: |-
        data='{"password":"[CHANGE_ME:YourEVCCPassword]"}'; ip='http://[CHANGE_ME:YourEVCCServerIP]:7070';\
        c=$(curl -H 'Content-Type: application/json' -d $data -ksc - $ip/api/auth/login -o /dev/null);\
        echo "${c}" | curl -ksb - $ip/api/config/devices/vehicle/[CHANGE_ME:YourVehicleId]/status
      json_attributes_path: '$.result.range'
      json_attributes:
        - value
      value_template: '{{ value_json.result.soc.value | float }}'
      unit_of_measurement: '%'
      # the scan_interval will be specified in seconds...
      # for update every 5min use 300 (60sec * 5min = 300sec)
      # for update every 15min use 900 (60sec * 15min = 900sec)
      # for update every 1h use 3600 (60sec * 60min = 3600sec)
      # for update every 24h use 86400 (60sec * 60min * 24h = 86400sec)
      scan_interval: 900
```

Here is a complete example assuming:
- that your `vehicle_id` is: __ford_mach_e__
- the IP of your evcc server is: __192.168.2.213__
- the EVCC password is: __myEvCCPwd__
and you want to capture the __soc__ as main entity information and the `range` as additional attribute of the entity that will be requested every 5 minutes:

```yaml
  - sensor:
      name: 'My Ford Mach-E SOC & Range'
      unique_id: evcc_mach_e_soc_and_range
      command: |-
        data='{"password":"myEvCCPwd"}'; ip='http://192.168.2.213:7070';\
        c=$(curl -H 'Content-Type: application/json' -d $data -ksc - $ip/api/auth/login -o /dev/null);\
        echo "${c}" | curl -ksb - $ip/api/config/devices/vehicle/ford_mach_e/status
      json_attributes_path: '$.result.range'
      json_attributes:
        - value
      value_template: '{{ value_json.result.soc.value | float }}'
      unit_of_measurement: '%'
      scan_interval: 300
```
### Don't want to store your evcc password in the ha configuration.yaml?
[@BDBAfH was so kind to post an alternative example here](https://github.com/marq24/ha-evcc/discussions/137), showing the way how to store and use the evcc password from a separate file.

## Want to report an issue?

Please use the [GitHub Issues](https://github.com/marq24/ha-evcc/issues) for reporting any issues you encounter with this integration. Please be so kind before creating a new issues, check the closed ones if your problem has been already reported (& solved).

To speed up the support process, you might like to already prepare and provide DEBUG log output. In the case of a technical issue, I would need this DEBUG log output to be able to help/fix the issue. There is a short [tutorial/guide 'How to provide DEBUG log' here](https://github.com/marq24/ha-senec-v3/blob/master/docs/HA_DEBUG.md) — please take the time to quickly go through it.

For this integration, you need to add:
```
logger:
  default: warning
  logs:
    custom_components.evcc_intg: debug
```

---

###### Advertisement / Werbung - alternative way to support me

### Switch to Tibber!

Be smart switch to Tibber - that's what I did in october 2023. If you want to join Tibber (become a customer), you might want to use my personal invitation link. When you use this link, Tibber will grant you and me a bonus of 50,-€ for each of us. This bonus then can be used in the Tibber store (not for your power bill) — e.g. to buy a Tibber Bridge. If you are already a Tibber customer and have not used an invitation link yet, you can also enter one afterward in the Tibber App (up to 14 days). [[see official Tibber support article](https://support.tibber.com/en/articles/4601431-tibber-referral-bonus#h_ae8df266c0)]

Please consider [using my personal Tibber invitation link to join Tibber today](https://invite.tibber.com/6o0kqvzf) or Enter the following code: 6o0kqvzf (six, oscar, zero, kilo, quebec, victor, zulu, foxtrot) afterward in the Tibber App - TIA!

---

### References

- https://github.com/evcc-io/evcc
- https://docs.evcc.io/docs/reference/api


[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Default-blue?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=ccc

[ghs]: https://github.com/sponsors/marq24
[ghsbadge]: https://img.shields.io/github/sponsors/marq24?style=for-the-badge&logo=github&logoColor=ccc&link=https%3A%2F%2Fgithub.com%2Fsponsors%2Fmarq24&label=Sponsors

[buymecoffee]: https://www.buymeacoffee.com/marquardt24
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a-coffee-blue.svg?style=for-the-badge&logo=buymeacoffee&logoColor=ccc

[paypal]: https://paypal.me/marq24
[paypalbadge]: https://img.shields.io/badge/paypal-me-blue.svg?style=for-the-badge&logo=paypal&logoColor=ccc

[hainstall]: https://my.home-assistant.io/redirect/config_flow_start/?domain=evcc_intg
[hainstallbadge]: https://img.shields.io/badge/dynamic/json?style=for-the-badge&logo=home-assistant&logoColor=ccc&label=usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.evcc_intg.total
