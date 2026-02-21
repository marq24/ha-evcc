# Use evcc with your Home Assistant sensor data

[evcc](https://github.com/evcc-io/evcc) is a common interface to charge electric vehicles. By default, evcc fetching the required data (meters/sites: grid, PV & battery states) directly from your PV/Battery System. This implies that the load on your PV/Battery system will increase and this could lead unfortunately to internal errors (this just happens to me when I tried to configue evcc via the default SENEC template included in evcc).

__We have already all data (evcc needs) in Home Assistant!__ — so why not use this information and provide it to evcc? The good news is, that this is possible — the bad news is, that' IMHO way to complicate for the average user to configure this.

So I will provide here an example evcc.yml (meters and site section) that can be used in order that evcc will be fed with data from your HA installation (having my SENEC.Home Integration installed).

This tutorial could be used also with other solar integrations — but you need to replace the corresponding sensor entities with the ones that match. 

## Preparation: 1'st Make Home Assistant sensor data accessible via API calls

As mentioned in the introduction, with the SENEC.Home integration for HA we have already all home-installation data evcc going to need — we just need a way to provide this HA sensor data to evcc.

### Create a Long-lived access token

Before we can use the HA-API to read sensor data via http, we need some sort of access (for evcc) to the API. Therefor you need to create so-called __Long-lived access token__. This can be done in the _Security_ tab of your _Profile_.

You can open this via `http://[YOUR-HA-INSTANCE]:8123/profile/security`

![screenshot_tokens](https://github.com/marq24/ha-senec-v3/blob/master/images/evcc_token01.png)

Create a new token via the _Create Token_ button, specify a name (e.g. 'evcc-access') and then copy the generated token to your clipboard (and paste it to a secure place). A token will look like this:

`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIzNWVjNzg5M2Y0ZjQ0MzBmYjUwOGEwMmU4N2Q0MzFmNyIsImlhdCI6MTcxNTUwNzYxMCwiZXhwIjoyMDMwODY3NjEwfQ.GMWO8saHpawkjNzk-uokxYeaP0GFKPQSeDoP3lCO488`

Please do not share your token anywhere! [the token above is really just an example!] — you need to replace all occurrences of `[YOUR-TOKEN-HERE]` in the following example evcc.yml section with __your generated token__. 

## Preparation: 2'nd Collect all required Home Assistant sensor names

This step is only required, if you want to use alternative HA sensors. In order to support the core features of evcc we need at least current grid power. __SENEC.Home.V4 users must use the alternative sensors as they are provided by the 'webapi'__.  But since this is a SENEC.Home tutorial I will provide here (my) full list of sensors:

- __GRID__:
  - Power (negative when exporting power to the grid, positive when importing power from the grid)
    - `sensor.senec_grid_state_power`
  - Current of P1,P2 & P3:
    - `sensor.senec_enfluri_net_current_p1`
    - `sensor.senec_enfluri_net_current_p2`
    - `sensor.senec_enfluri_net_current_p3`

     
- __PV__:
  - Generated power by PV (total):
    - `sensor.senec_solar_generated_power`

    
- __Battery__:
  - Battery power, negative when consumed by battery (charging) (Please note, that evcc expects a positive value when battery will be charged and a negative when energy from battery will be consumed — we deal with this in the meters configuration later)
    - `sensor.senec_battery_state_power`
  - State of Charge (in percent) 
    - `sensor.senec_battery_charge_percent`


- _Optional_ __Aux__:
  - Electrical consumption of my waterkotte heatpump:
    - `sensor.wkh_power_electric`

  - Electrical consumption of my pool pump & heating (Shelly):
    - `sensor.kanal_1_pool_power`
    
  - Electrical consumption of my garden (water) pump (Shelly):
    - `sensor.kanal_2_power`


## Example evcc.yaml (`meters` section)

### Required replacements

Below you will find a valid evcc meters configuration — __but you have to make two replacements__:
1. The text '__[YOUR-HA-INSTANCE]__' has to be replaced with the IP/host name of your Home Assistant installation.
    
    E.g., when your HA is reachable via: http://192.168.10.20:8123, then you need to replace `[YOUR-HA-INSTANCE]` with `192.168.10.20`


2. The text '__[YOUR-TOKEN-HERE]__' has to be replaced with the _Long-lived access token_ you have just created in HA.

   E.g. when your token is: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIzNWVjNzg5M2Y0ZjQ0MzBmYjUwOGEwMmU4N2Q0MzFmNyIsImlhdCI6MTcxNTUwNzYxMCwiZXhwIjoyMDMwODY3NjEwfQ.GMWO8saHpawkjNzk-uokxYeaP0GFKPQSeDoP3lCO488`, then you need to replace `[YOUR-TOKEN-HERE]` with this (long) token text.

So as a short example (with all replacements) would look like:

```
      ...
      source: http
      uri: http://192.168.10.20:8123/api/states/sensor.senec_grid_state_power
      method: GET
      headers:
        - Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIzNWVjNzg5M2Y0ZjQ0MzBmYjUwOGEwMmU4N2Q0MzFmNyIsImlhdCI6MTcxNTUwNzYxMCwiZXhwIjoyMDMwODY3NjEwfQ.GMWO8saHpawkjNzk-uokxYeaP0GFKPQSeDoP3lCO488
      insecure: true
      ...
```

### Complete sample evcc.yaml meters section for SENEC.Home Sensors
```yaml
meters:
  - name: SENEC.grid
    type: custom
    power:
      source: http
      uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.senec_grid_state_power
      method: GET
      headers:
        - Authorization: Bearer [YOUR-TOKEN-HERE]
      insecure: true
      jq: .state|tonumber
      timeout: 2s
    currents:
      - source: http
        uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.senec_enfluri_net_current_p1
        method: GET
        headers:
          - Authorization: Bearer [YOUR-TOKEN-HERE]
        insecure: true
        jq: .state|tonumber
        timeout: 2s
      - source: http
        uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.senec_enfluri_net_current_p2
        method: GET
        headers:
          - Authorization: Bearer [YOUR-TOKEN-HERE]
        insecure: true
        jq: .state|tonumber
        timeout: 2s
      - source: http
        uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.senec_enfluri_net_current_p3
        method: GET
        headers:
          - Authorization: Bearer [YOUR-TOKEN-HERE]
        insecure: true
        jq: .state|tonumber
        timeout: 2s

  - name: SENEC.pv
    type: custom
    power:
      source: http
      uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.senec_solar_generated_power
      method: GET
      headers:
        - Authorization: Bearer [YOUR-TOKEN-HERE]
      insecure: true
      jq: .state|tonumber
      timeout: 2s

  - name: SENEC.bat
    type: custom
    power:
      source: http
      uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.senec_battery_state_power
      method: GET
      headers:
        - Authorization: Bearer [YOUR-TOKEN-HERE]
      insecure: true
      jq: .state|tonumber * -1 # this does the trick to invert the sensor value for evcc
      timeout: 2s
    soc:
      source: http
      uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.senec_battery_charge_percent
      method: GET
      headers:
        - Authorization: Bearer [YOUR-TOKEN-HERE]
      insecure: true
      jq: .state|tonumber
      timeout: 2s
```

### My additional AUX entries 

Just to demonstrate the general concept of adding additional AUX senors (all this will be part of the evcc.yaml meters section)

```
  - name: AUX.heat
    type: custom
    power:
      source: http
      uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.wkh_power_electric
      method: GET
      headers:
        - Authorization: Bearer [YOUR-TOKEN-HERE]
      insecure: true
      jq: .state|tonumber
      timeout: 2s

  - name: AUX.pool
    type: custom
    power:
      source: http
      uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.kanal_1_pool_power
      method: GET
      headers:
        - Authorization: Bearer [YOUR-TOKEN-HERE]
      insecure: true
      jq: .state|tonumber
      timeout: 2s

  - name: AUX.gardenpump
    type: custom
    power:
      source: http
      uri: http://[YOUR-HA-INSTANCE]:8123/api/states/sensor.kanal_2_power
      method: GET
      headers:
        - Authorization: Bearer [YOUR-TOKEN-HERE]
      insecure: true
      jq: .state|tonumber
      timeout: 2s
```

## Final step: configure the evcc `site`

Use the following meters in your evcc.ymal `site` configuration (obviously use the `aux` only if you have similar entries):

```
site:
  ...
  meters:
    grid: SENEC.grid
    pv:
      - SENEC.pv
    battery:
      - SENEC.bat
    aux:
      - AUX.heat
      - AUX.pool
      - AUX.gardenpump
  ...
```

# Summary

1. Create a [Long-lived access token in HA](http://[YOUR-HA-INSTANCE]:8123/profile/security)
2. Configure the different evcc meter's (in evcc.yaml) via the `type: custom` and provide `power` (& `currents` and/or `soc`)
3. _Optional_: Add additional AUX sources
4. Configure your evcc site
5. Be happy evcc user __without putting extra load__ on your SENEC.Home!


## Enable evcc TRACE logging

When you have issues with the http requests to your HA instance, you might like to enable TRACE log level of evcc to find the root cause.

### Trace log level in evcc.yaml
```
log: trace
```


# Additional Resources:
- [Create __Long-lived access Token__ in HA](https://github.com/marq24/ha-evcc/blob/main/HA_AS_EVCC_SOURCE.md#preparation-1st-make-home-assistant-sensor-data-accessible-via-api-calls)
- [Provide HA PV/Grid Data to evcc](https://github.com/marq24/ha-evcc/blob/main/HA_AS_EVCC_SOURCE.md)
- [Provide HA vehicle data to evcc](https://github.com/marq24/ha-fordpass/blob/main/doc/EVCC.md)
- [Let evcc control your HA entities (PV surplus handling)](https://github.com/marq24/ha-evcc/blob/main/HA_CONTROLLED_BY_EVCC.md)
