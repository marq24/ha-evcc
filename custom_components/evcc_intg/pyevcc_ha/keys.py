import logging
import re
from enum import Enum
from typing import (
    NamedTuple, Final
)

from custom_components.evcc_intg.pyevcc_ha.const import (
    MIN_CURRENT_LIST,
    MAX_CURRENT_LIST,
    JSONKEY_LOADPOINTS,
    JSONKEY_VEHICLES,
    JSONKEY_STATISTICS,
    JSONKEY_STATISTICS_TOTAL,
    JSONKEY_STATISTICS_THISYEAR,
    JSONKEY_STATISTICS_365D,
    JSONKEY_STATISTICS_30D,
    BATTERY_LIST
)

# from aenum import Enum, extend_enum

_LOGGER: logging.Logger = logging.getLogger(__package__)

IS_TRIGGER: Final = "TRIGGER"

CC_P1: Final = re.compile(r"(.)([A-Z][a-z]+)")
CC_P2: Final = re.compile(r"([a-z0-9])([A-Z])")

def camel_to_snake(a_key: str):
    if a_key.lower().endswith("kwh"):
        a_key = a_key[:-3] + "_kwh"
    a_key = re.sub(CC_P1, r'\1_\2', a_key)
    return re.sub(CC_P2, r'\1_\2', a_key).lower()

class EP_TYPE(Enum):
    LOADPOINTS = JSONKEY_LOADPOINTS
    VEHICLES = JSONKEY_VEHICLES
    STATISTICS = JSONKEY_STATISTICS
    SITE = "site"
    TARIFF = "tariff"

class BATTERY_CONTENT(Enum):
    SOC = "soc"
    POWER = "power"

class GRID_CONTENT(Enum):
    CURRENTS = "currents"
    POWER = "power"

class PV_CONTENT(Enum):
    ENERGY = "energy"
    POWER = "power"

class FORECAST_CONTENT(Enum):
    GRID = "grid"
    SOLAR = "solar"

class ApiKey(NamedTuple):
    key: str
    type: str
    key_alias: str = None
    subtype: str = None
    entity_key: str = None
    write_key: str = None
    write_type: str = None
    options: list[str] = None
    writeable: bool = False

    @property
    def snake_case(self) -> str:
        return camel_to_snake(self.key)

# see https://docs.evcc.io/docs/reference/api for details
class Tag(ApiKey, Enum):

    def __hash__(self) -> int:
        if self.entity_key is not None:
            return hash(f"{self.key}.{self.entity_key}")
        else:
            return hash(self.key)

    def __str__(self):
        if self.entity_key is not None:
            return f"{self.key}.{self.entity_key}"
        else:
            return self.key

    ###################################
    # SITE STUFF
    ###################################

    # "auxPower": 1116.8,
    AUXPOWER = ApiKey(key="auxPower", type=EP_TYPE.SITE)

    # "batteryMode": unknown|normal|hold|charge
    BATTERYMODE = ApiKey(key="batteryMode", type=EP_TYPE.SITE)

    # "batteryPower": 3.21,
    BATTERYPOWER = ApiKey(key="batteryPower", type=EP_TYPE.SITE)

    # "batterySoc": 70,
    BATTERYSOC = ApiKey(key="batterySoc", type=EP_TYPE.SITE)

    # "batteryCapacity": 7.5,
    BATTERYCAPACITY = ApiKey(key="batteryCapacity", type=EP_TYPE.SITE)

    # "battery":[{"power":0,"capacity":12,"soc":81,"controllable":false}], -> we must access this attribute via tuple_idx
    BATTERY = ApiKey(key="battery", type=EP_TYPE.SITE)

    # "pvPower": 8871.22,
    PVPOWER = ApiKey(key="pvPower", type=EP_TYPE.SITE)

    # "pvEnergy": 4235.825,
    PVENERGY = ApiKey(key="pvEnergy", type=EP_TYPE.SITE)

    # "pv": [{"power": 8871.22}], -> we must access this attribute via tuple_idx
    PV = ApiKey(key="pv", type=EP_TYPE.SITE)

    # "gridCurrents": [17.95, 7.71, 1.99],
    GRIDCURRENTS = ApiKey(key="gridCurrents", type=EP_TYPE.SITE)

    # "gridPower": -6280.24,
    GRIDPOWER = ApiKey(key="gridPower", type=EP_TYPE.SITE)

    # "grid": { "currents": [17.95, 7.71, 1.99],
    #           "power": -6280.24,
    #           ...}
    GRID = ApiKey(key="grid", type=EP_TYPE.SITE)

    # "homePower": 2594.19,
    HOMEPOWER = ApiKey(key="homePower", type=EP_TYPE.SITE)

    # -> NONE FREQUENT
    # POST /api/batterydischargecontrol/<status>: enable/disable battery discharge control (true/false)
    BATTERYDISCHARGECONTROL = ApiKey(
        key="batteryDischargeControl", type=EP_TYPE.SITE, writeable=True, write_key="batterydischargecontrol"
    )

    # POST /api/residualpower/<power>: grid residual power in W
    RESIDUALPOWER = ApiKey(key="residualPower", type=EP_TYPE.SITE, writeable=True, write_key="residualpower")

    # POST /api/prioritysoc/<soc>: battery priority soc in %
    PRIORITYSOC = ApiKey(
        key="prioritySoc", type=EP_TYPE.SITE, writeable=True, write_key="prioritysoc", options=BATTERY_LIST
    )

    # POST /api/buffersoc/<soc>: battery buffer soc in %
    BUFFERSOC = ApiKey(
        key="bufferSoc", type=EP_TYPE.SITE, writeable=True, write_key="buffersoc", options=BATTERY_LIST[1:]
    )

    # POST /api/bufferstartsoc/<soc>: battery buffer start soc in %
    BUFFERSTARTSOC = ApiKey(
        key="bufferStartSoc", type=EP_TYPE.SITE, writeable=True, write_key="bufferstartsoc",
        options=BATTERY_LIST[1:]+BATTERY_LIST[0:1]
    )

    # when 'POST /api/smartcostlimit/<cost>:' smart charging cost limit (previously known as "cheap" tariff)
    # ALL smartCostLimit of all loadpoints will be set
    # SMARTCOSTLIMIT = ApiKey(key="smartCostLimit", type=EP_TYPE.SITE, writeable=True, write_key="smartcostlimit")

    AVAILABLEVERSION = ApiKey(key="availableVersion", type=EP_TYPE.SITE)

    VERSION = ApiKey(key="version", type=EP_TYPE.SITE)

    # "tariffGrid": 0.233835,
    TARIFFGRID = ApiKey(key="tariffGrid", type=EP_TYPE.SITE)

    # "tariffPriceHome": 0,
    TARIFFPRICEHOME = ApiKey(key="tariffPriceHome", type=EP_TYPE.SITE)

    # -> NONE FREQUENT
    # POST /api/batterydischargecontrol/<status>: enable/disable battery discharge control (true/false)
    # batteryGridChargeActive: false,
    BATTERYGRIDCHARGEACTIVE = ApiKey(key="batteryGridChargeActive", type=EP_TYPE.SITE, write_key="batterygridchargeactive")

    # batteryGridChargeLimit: ??
    BATTERYGRIDCHARGELIMIT = ApiKey(key="batteryGridChargeLimit", type=EP_TYPE.SITE, write_key="batterygridchargelimit")

    FORECAST_GRID = ApiKey(entity_key="forecast_grid", key="forecast", type=EP_TYPE.SITE)
    FORECAST_SOLAR = ApiKey(entity_key="forecast_solar", key="forecast", type=EP_TYPE.SITE)

    ###################################
    # LOADPOINT-DATA
    ###################################

    # "chargeCurrent": 0,
    # key_alias is a new property of a tag, that allows to specify a second json key
    # -> that is useful, when an attribute will be renamed in the source API
    CHARGECURRENT = ApiKey(key="chargeCurrent", key_alias="offeredCurrent", type=EP_TYPE.LOADPOINTS)

    # "chargeCurrents": [0, 0, 0],
    CHARGECURRENTS = ApiKey(key="chargeCurrents", type=EP_TYPE.LOADPOINTS)

    # "chargeDuration": 0, -> (in millis) ?! 840000000000 = 14min -> / 1000000
    CHARGEDURATION = ApiKey(key="chargeDuration", type=EP_TYPE.LOADPOINTS)
    CHARGEREMAININGDURATION = ApiKey(key="chargeRemainingDuration", type=EP_TYPE.LOADPOINTS)

    # "chargePower": 0,
    CHARGEPOWER = ApiKey(key="chargePower", type=EP_TYPE.LOADPOINTS)

    # "chargeTotalImport": 0.004,
    CHARGETOTALIMPORT = ApiKey(key="chargeTotalImport", type=EP_TYPE.LOADPOINTS)

    # "chargedEnergy": 0,
    CHARGEDENERGY = ApiKey(key="chargedEnergy", type=EP_TYPE.LOADPOINTS)
    CHARGEREMAININGENERGY = ApiKey(key="chargeRemainingEnergy", type=EP_TYPE.LOADPOINTS)

    # "chargerFeatureHeating": false,
    # "chargerFeatureIntegratedDevice": false,
    # "chargerIcon": null,
    # "chargerPhases1p3p": true,
    # "chargerPhysicalPhases": null,

    # "charging": false,
    CHARGING = ApiKey(key="charging", type=EP_TYPE.LOADPOINTS)

    # "connected": false,
    CONNECTED = ApiKey(key="connected", type=EP_TYPE.LOADPOINTS)

    # "connectedDuration": 9.223372036854776e+18,
    CONNECTEDDURATION = ApiKey(key="connectedDuration", type=EP_TYPE.LOADPOINTS)

    # "effectiveLimitSoc": 100,
    EFFECTIVELIMITSOC = ApiKey(key="effectiveLimitSoc", type=EP_TYPE.LOADPOINTS)

    # "effectiveMaxCurrent": 16,
    # "effectiveMinCurrent": 6,
    # "effectivePriority": 0,

    # "planActive": false,
    PLANACTIVE = ApiKey(key="planActive", type=EP_TYPE.LOADPOINTS)
    # this value is NOT present in the data - and must be calculated internally
    PLANACTIVEALT = ApiKey(key="planActiveAlt", type=EP_TYPE.LOADPOINTS)
    # "effectivePlanSoc": 0,
    EFFECTIVEPLANSOC = ApiKey(key="effectivePlanSoc", type=EP_TYPE.LOADPOINTS)
    # "effectivePlanTime": "0001-01-01T00:00:00Z",
    EFFECTIVEPLANTIME = ApiKey(key="effectivePlanTime", type=EP_TYPE.LOADPOINTS)
    # "planProjectedEnd": "2025-02-20T13:34:32+01:00",
    PLANPROJECTEDEND = ApiKey(key="planProjectedEnd", type=EP_TYPE.LOADPOINTS)
    # "planProjectedStart": "2025-02-20T13:00:00+01:00",
    PLANPROJECTEDSTART = ApiKey(key="planProjectedStart", type=EP_TYPE.LOADPOINTS)

    # "enabled": false,
    ENABLED = ApiKey(key="enabled", type=EP_TYPE.LOADPOINTS)

    # "phaseAction": "inactive",
    PHASEACTION = ApiKey(key="phaseAction", type=EP_TYPE.LOADPOINTS)

    # "phaseRemaining": 0,
    PHASEREMAINING = ApiKey(key="phaseRemaining", type=EP_TYPE.LOADPOINTS)

    # "phasesActive": 3,
    PHASESACTIVE = ApiKey(key="phasesActive", type=EP_TYPE.LOADPOINTS)

    # "phasesEnabled": 0,
    PHASESENABLED = ApiKey(key="phasesEnabled", type=EP_TYPE.LOADPOINTS)

    # "planOverrun": 0,
    PLANOVERRUN = ApiKey(key="planOverrun", type=EP_TYPE.LOADPOINTS)
    
    # "priority": 0,

    # "pvAction": "inactive", "activ", "disable"
    PVACTION = ApiKey(key="pvAction", type=EP_TYPE.LOADPOINTS)
    # "pvRemaining": 0,
    PVREMAINING = ApiKey(key="pvRemaining", type=EP_TYPE.LOADPOINTS)
    # "enableDelay": 60,
    ENABLEDELAY = ApiKey(key="enableDelay", write_key="enable/delay", type=EP_TYPE.LOADPOINTS)
    # "disableDelay": 180,
    DISABLEDELAY = ApiKey(key="disableDelay", write_key="disable/delay", type=EP_TYPE.LOADPOINTS)

    # "sessionCo2PerKWh": null,
    SESSIONCO2PERKWH = ApiKey(key="sessionCo2PerKWh", type=EP_TYPE.LOADPOINTS)
    # "sessionEnergy": 0,
    SESSIONENERGY = ApiKey(key="sessionEnergy", type=EP_TYPE.LOADPOINTS)
    # "sessionPrice": null,
    SESSIONPRICE = ApiKey(key="sessionPrice", type=EP_TYPE.LOADPOINTS)
    # "sessionPricePerKWh": null,
    SESSIONPRICEPERKWH = ApiKey(key="sessionPricePerKWh", type=EP_TYPE.LOADPOINTS)
    # "sessionSolarPercentage": 0,
    SESSIONSOLARPERCENTAGE = ApiKey(key="sessionSolarPercentage", type=EP_TYPE.LOADPOINTS)

    # "smartCostActive": true,
    SMARTCOSTACTIVE = ApiKey(key="smartCostActive", type=EP_TYPE.LOADPOINTS)

    # "smartCostLimit": 0.22,
    SMARTCOSTLIMIT = ApiKey(key="smartCostLimit", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="smartcostlimit")

    # "title": "HH-7",
    # -> USED during startup phase

    # "vehicleClimaterActive": null,
    # ???

    # start Vehicle Detection Button
    DETECTVEHICLE = ApiKey(key="detectvehicle", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="detectvehicle")

    # "vehicleDetectionActive": false,
    VEHICLEDETECTIONACTIVE = ApiKey(key="vehicleDetectionActive", type=EP_TYPE.LOADPOINTS)

    # "vehicleName": "",
    VEHICLENAME = ApiKey(key="vehicleName", type=EP_TYPE.LOADPOINTS, writeable=True, write_key = "vehicle")

    # "vehicleOdometer": 0,
    VEHICLEODOMETER = ApiKey(key="vehicleOdometer", type=EP_TYPE.LOADPOINTS)

    # "vehicleRange": 0,
    VEHICLERANGE = ApiKey(key="vehicleRange", type=EP_TYPE.LOADPOINTS)

    # "vehicleSoc": 0
    VEHICLESOC = ApiKey(key="vehicleSoc", type=EP_TYPE.LOADPOINTS)

    # "vehicleClimaterActive": null,
    VEHICLECLIMATERACTIVE = ApiKey(key="vehicleClimaterActive", type=EP_TYPE.LOADPOINTS)

    #"vehicleWelcomeActive": false
    VEHICLEWELCOMEACTIVE = ApiKey(key="vehicleWelcomeActive", type=EP_TYPE.LOADPOINTS)

    # "mode": "off", -> (off/pv/minpv/now)
    MODE = ApiKey(
        key="mode", type=EP_TYPE.LOADPOINTS,
        writeable=True, write_key="mode", options=["off", "pv", "minpv", "now"]
    )
    # "limitSoc": 0, -> write 'limitsoc' in %
    LIMITSOC = ApiKey(key="limitSoc", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="limitsoc")

    # "limitEnergy": 0, -> write 'limitenergy' limit energy in kWh
    LIMITENERGY = ApiKey(key="limitEnergy", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="limitenergy")

    # "phasesConfigured": 0, -> write 'phases' -> allowed phases (0=auto/1=1p/3=3p)
    PHASES = ApiKey(
        key="phasesConfigured", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="phases", options=["0", "1", "3"]
    )

    # "minCurrent": 6, -> write 'mincurrent' current minCurrent value in A
    MINCURRENT = ApiKey(
        key="minCurrent", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="mincurrent", options=MIN_CURRENT_LIST
    )

    # "maxCurrent": 16, -> write 'maxcurrent' current maxCurrent value in A
    MAXCURRENT = ApiKey(
        key="maxCurrent", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="maxcurrent", options=MAX_CURRENT_LIST
    )

    # enable/disable BatteryBoost (per Loadpoint)
    BATTERYBOOST = ApiKey(key="batteryBoost", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="batteryboost")

    # "disableThreshold": 0, -> write 'disable/threshold' (in W)
    DISABLETHRESHOLD = ApiKey(
        key="disableThreshold", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="disable/threshold"
    )

    # "enableThreshold": 0, -> write 'enable/threshold' (in W)
    ENABLETHRESHOLD = ApiKey(
        key="enableThreshold", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="enable/threshold"
    )

    # values can be written via SERVICE
    # "planEnergy": 0,
    PLANENERGY = ApiKey(key="planEnergy", type=EP_TYPE.LOADPOINTS)

    # "planTime": "0001-01-01T00:00:00Z",
    PLANTIME = ApiKey(key="planTime", type=EP_TYPE.LOADPOINTS)

    # delete plan button
    PLANDELETE = ApiKey(key="planDelete", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="plan/energy")

    ###################################
    # VEHICLE
    ###################################

    # "vehicleLimitSoc": 0, -> write to vehicle EP!
    # even if we write to 'limitsoc' at the vehicle endpoint, the loadpoint[n]:vehicleLimitSoc values does not change ?!
    VEHICLELIMITSOC = ApiKey(
        key="limitSoc", type=EP_TYPE.VEHICLES, writeable=True, write_key="limitsoc", options=BATTERY_LIST
    )
    VEHICLEMINSOC = ApiKey(
        key="minSoc", type=EP_TYPE.VEHICLES, writeable=True, write_key="minsoc", options=BATTERY_LIST[:-1]
    )

    # values can be written via SERVICE
    VEHICLEPLANSSOC = ApiKey(key="vehiclePlansSoc", type=EP_TYPE.VEHICLES)
    VEHICLEPLANSTIME = ApiKey(key="vehiclePlansTime", type=EP_TYPE.VEHICLES)
    # delete plan button
    VEHICLEPLANSDELETE= ApiKey(key="vehiclePlansDelete", type=EP_TYPE.VEHICLES, writeable=True, write_key="plan/soc")

    ###################################
    # STATISTICS
    ###################################

    STATTOTALAVGCO2 = ApiKey(entity_key="statTotalAvgCo2", key="avgCo2", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_TOTAL)
    STATTOTALAVGPRICE = ApiKey(entity_key="statTotalAvgPrice", key="avgPrice", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_TOTAL)
    STATTOTALCHARGEDKWH = ApiKey(entity_key="statTotalChargedKWh", key="chargedKWh", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_TOTAL)
    STATTOTALSOLARPERCENTAGE = ApiKey(entity_key="statTotalSolarPercentage", key="solarPercentage", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_TOTAL)

    STATTHISYEARAVGCO2 = ApiKey(entity_key="statThisYearAvgCo2", key="avgCo2", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_THISYEAR)
    STATTHISYEARAVGPRICE = ApiKey(entity_key="statThisYearAvgPrice", key="avgPrice", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_THISYEAR)
    STATTHISYEARCHARGEDKWH = ApiKey(entity_key="statThisYearChargedKWh", key="chargedKWh", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_THISYEAR)
    STATTHISYEARSOLARPERCENTAGE = ApiKey(entity_key="statThisYearSolarPercentage", key="solarPercentage", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_THISYEAR)

    STAT365AVGCO2 = ApiKey(entity_key="stat365AvgCo2", key="avgCo2", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_365D)
    STAT365AVGPRICE = ApiKey(entity_key="stat365AvgPrice", key="avgPrice", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_365D)
    STAT365CHARGEDKWH = ApiKey(entity_key="stat365ChargedKWh", key="chargedKWh", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_365D)
    STAT365SOLARPERCENTAGE = ApiKey(entity_key="stat365SolarPercentage", key="solarPercentage", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_365D)

    STAT30AVGCO2 = ApiKey(entity_key="stat30AvgCo2", key="avgCo2", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_30D)
    STAT30AVGPRICE = ApiKey(entity_key="stat30AvgPrice", key="avgPrice", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_30D)
    STAT30CHARGEDKWH = ApiKey(entity_key="stat30ChargedKWh", key="chargedKWh", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_30D)
    STAT30SOLARPERCENTAGE = ApiKey(entity_key="stat30SolarPercentage", key="solarPercentage", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_30D)

    TARIF_GRID = ApiKey(entity_key="tariff_api_grid", key="grid", type=EP_TYPE.TARIFF)
    TARIF_SOLAR = ApiKey(entity_key="tariff_api_solar", key="solar", type=EP_TYPE.TARIFF)