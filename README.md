# Home Assistant Integration: __evcc☀️🚘- Solar Charging__ (unofficial)

![logo](https://github.com/marq24/ha-evcc/raw/main/logo.png)

I was surprised that looks like that there does not exist a simple Home Assistant integration for evcc - even if I do not believe that I have the need for evcc at all, I want to contribute a very simple & basic integration which allow you to control evcc objects simply via the default HA gui.

__Please note__, _that this integration is not official and not supported by the evcc developers. I am not affiliated with evcc in any way. This integration is based on the evcc API and the evcc API documentation._

[![hacs_badge][hacsbadge]][hacs] [![github][ghsbadge]][ghs] [![BuyMeCoffee][buymecoffeebadge]][buymecoffee] [![PayPal][paypalbadge]][paypal] [![hainstall][hainstallbadge]][hainstall]

## Disclaimer

Please be aware, that we are developing this integration to best of our knowledge and belief, but cant give a guarantee. Therefore, use this integration **at your own risk**.

## Requirements

- A running & configured evcc instance in your network

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

Just take a look at this sample Dashboard (showing Sensors from one load point):

![sampledashboard](https://github.com/marq24/ha-evcc/raw/main/sample-dashboard.png)

## Installation

### via HACS

1. Add a custom integration repository to HACS: [https://github.com/marq24/ha-evcc](https://github.com/marq24/ha-evcc)
2. Install the custom integration
3. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "evcc☀️🚘- Solar Charging"
4. Setup the go-eCharger custom integration as described below

  <!--1. In HACS Store, search for [***marq24/ha-evcc***]-->

### manual steps

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `evcc_intg`.
4. Download _all_ the files from the `custom_components/evcc_intg/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "evcc☀️🚘- Solar Charging"

## Adding or enabling the integration

### My Home Assistant (2021.3+)

Just click the following Button to start the configuration automatically:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=evcc_intg)

### Manual steps

Use the following steps for a manual configuration by adding the custom integration using the web interface and follow instruction on screen:

- Go to `Configuration -> Integrations` and add "evcc☀️🚘- Solar Charging" integration
- Provide a unique name for the integration installation (will be used in each sensor entity_id) created by the integration
- Provide the URL of your evcc web server (including the port) - e.g. `http://your-evcc-ip-here:7070`
- Provide area where the wallbox is located

After the integration was added you can use the 'config' button to adjust your settings, you can additionally modify the update interval

Please note, that some of the available sensors are __not__ enabled by default.

## Use evcc with your Home Assistant sensor data

Please see the separate document where you can find examples [how to provide your evcc instance with HA sensor data](https://github.com/marq24/ha-evcc/blob/main/HA_AS_EVCC_SOURCE.md).

## Are you are go-eCharger V3 (or higher) User?

Do you know, that as owners of a go-eCharger (V3+) there is no need to use evcc for solar surplus charging? Even without any additional hardware! Home Assistant and the __go-eCharger APIv2 Connect__ Integration is all you need. Get all details from [https://github.com/marq24/ha-goecharger-api2](https://github.com/marq24/ha-goecharger-api2).

## Want to report an issue?

Please use the [GitHub Issues](https://github.com/marq24/ha-evcc/issues) for reporting any issues you encounter with this integration. Please be so kind before creating a new issues, check the closed ones, if your problem have been already reported (& solved).

In order to speed up the support process you might like already prepare and provide DEBUG log output. In the case of a technical issue, I would need this DEBUG log output to be able to help/fix the issue. There is a short [tutorial/guide 'How to provide DEBUG log' here](https://github.com/marq24/ha-senec-v3/blob/master/docs/HA_DEBUG.md) - please take the time to quickly go through it.

For this integration you need to add:
```
logger:
  default: warning
  logs:
    custom_components.evcc_intg: debug
```

---

###### Advertisement / Werbung - alternative way to support me

### Switch to Tibber!

Be smart switch to Tibber - that's what I did in october 2023. If you want to join Tibber (become a customer), you might want to use my personal invitation link. When you use this link, Tibber will we grant you and me a bonus of 50,-€ for each of us. This bonus then can be used in the Tibber store (not for your power bill) - e.g. to buy a Tibber Bridge. If you are already a Tibber customer and have not used an invitation link yet, you can also enter one afterward in the Tibber App (up to 14 days). [[see official Tibber support article](https://support.tibber.com/en/articles/4601431-tibber-referral-bonus#h_ae8df266c0)]

Please consider [using my personal Tibber invitation link to join Tibber today](https://invite.tibber.com/6o0kqvzf) or Enter the following code: 6o0kqvzf (six, oscar, zero, kilo, quebec, victor, zulu, foxtrot) afterward in the Tibber App - TIA!

---

### References

- https://github.com/evcc-io/evcc
- https://docs.evcc.io/docs/reference/api


[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=ccc

[ghs]: https://github.com/sponsors/marq24
[ghsbadge]: https://img.shields.io/github/sponsors/marq24?style=for-the-badge&logo=github&logoColor=ccc&link=https%3A%2F%2Fgithub.com%2Fsponsors%2Fmarq24&label=Sponsors

[buymecoffee]: https://www.buymeacoffee.com/marquardt24
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a-coffee-blue.svg?style=for-the-badge&logo=buymeacoffee&logoColor=ccc

[paypal]: https://paypal.me/marq24
[paypalbadge]: https://img.shields.io/badge/paypal-me-blue.svg?style=for-the-badge&logo=paypal&logoColor=ccc

[hainstall]: https://my.home-assistant.io/redirect/config_flow_start/?domain=evcc_intg
[hainstallbadge]: https://img.shields.io/badge/dynamic/json?style=for-the-badge&logo=home-assistant&logoColor=ccc&label=usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.evcc_intg.total