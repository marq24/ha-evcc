import logging
import re
from enum import Enum
from typing import (
    NamedTuple, Final
)

from custom_components.evcc_intg.pyevcc_ha.const import (
    MIN_CURRENT_LIST,
    MAX_CURRENT_LIST,
    JSONKEY_CIRCUITS,
    JSONKEY_LOADPOINTS,
    JSONKEY_VEHICLES,
    JSONKEY_EVOPT,
    JSONKEY_EVOPT_REQ,
    JSONKEY_EVOPT_RES,
    JSONKEY_EVOPT_DETAILS,
    JSONKEY_STATISTICS,
    JSONKEY_STATISTICS_TOTAL,
    JSONKEY_STATISTICS_THISYEAR,
    JSONKEY_STATISTICS_365D,
    JSONKEY_STATISTICS_30D,
    BATTERY_LIST,
    SESSIONS_KEY_VEHICLES,
    SESSIONS_KEY_LOADPOINTS
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
    CIRCUITS = JSONKEY_CIRCUITS
    LOADPOINTS = JSONKEY_LOADPOINTS
    VEHICLES = JSONKEY_VEHICLES
    STATISTICS = JSONKEY_STATISTICS
    EVOPT = JSONKEY_EVOPT
    SITE = "site"
    TARIFF = "tariff"
    SESSIONS = "sessions"

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
    FEEDIN = "feedin"
    PLANNER = "planner"

class ApiKey(NamedTuple):
    type: str
    json_key: str
    json_key_alias: str = None
    subtype: str = None
    entity_key: str = None

    write_key: str = None
    write_type: str = None
    options: list[str] = None
    writeable: bool = False

    @property
    def snake_case(self) -> str:
        return camel_to_snake(self.json_key)


# see https://docs.evcc.io/docs/reference/api for details
class Tag(ApiKey, Enum):

    def __hash__(self) -> int:
        if self.entity_key is not None:
            return hash(f"{self.json_key}.{self.entity_key}")
        else:
            return hash(self.json_key)

    def __str__(self):
        if self.entity_key is not None:
            return f"{self.json_key}.{self.entity_key}"
        else:
            return self.json_key

    ###################################
    # SITE STUFF
    ###################################

    # "auxPower": 1116.8,
    AUXPOWER = ApiKey(json_key="auxPower", type=EP_TYPE.SITE)

    # "batteryMode": unknown|normal|hold|charge
    BATTERYMODE = ApiKey(json_key="batteryMode", type=EP_TYPE.SITE)

    # "battery":[{"power":0,"capacity":12,"soc":81,"controllable":false}], -> we must access this attribute via json_idx
    BATTERY = ApiKey(json_key="battery", type=EP_TYPE.SITE)
    BATTERY_AS_OBJ = ApiKey(entity_key="batteryDevices", json_key="devices", subtype=BATTERY.json_key, type=EP_TYPE.SITE)

    # "batteryPower": 3.21,
    BATTERYPOWER = ApiKey(json_key="batteryPower", type=EP_TYPE.SITE)
    BATTERYPOWER_AS_OBJ = ApiKey(entity_key="batteryPower", json_key="power", subtype=BATTERY.json_key, type=EP_TYPE.SITE)

    # "batterySoc": 70,
    BATTERYSOC = ApiKey(json_key="batterySoc", type=EP_TYPE.SITE)
    BATTERYSOC_AS_OBJ = ApiKey(entity_key="batterySoc", json_key="soc", subtype=BATTERY.json_key, type=EP_TYPE.SITE)

    # "batteryCapacity": 7.5,
    BATTERYCAPACITY = ApiKey(json_key="batteryCapacity", type=EP_TYPE.SITE)
    BATTERYCAPACITY_AS_OBJ = ApiKey(entity_key="batteryCapacity", json_key="capacity", subtype=BATTERY.json_key, type=EP_TYPE.SITE)

    # "batteryEnergy": 0,
    BATTERYENERGY = ApiKey(json_key="batteryEnergy", type=EP_TYPE.SITE)
    BATTERYENERGY_AS_OBJ = ApiKey(entity_key="batteryEnergy", json_key="energy", subtype=BATTERY.json_key, type=EP_TYPE.SITE)

    # "pvPower": 8871.22,
    PVPOWER = ApiKey(json_key="pvPower", type=EP_TYPE.SITE)

    # "pvEnergy": 4235.825,
    PVENERGY = ApiKey(json_key="pvEnergy", type=EP_TYPE.SITE)

    # "pv": [{"power": 8871.22}], -> we must access this attribute via json_idx
    PV = ApiKey(json_key="pv", type=EP_TYPE.SITE)

    # "gridCurrents": [17.95, 7.71, 1.99],
    GRIDCURRENTS = ApiKey(json_key="gridCurrents", type=EP_TYPE.SITE)

    # "gridPower": -6280.24,
    GRIDPOWER = ApiKey(json_key="gridPower", type=EP_TYPE.SITE)

    # "grid": { "currents": [17.95, 7.71, 1.99],
    #           "power": -6280.24,
    #           ...}
    GRID = ApiKey(json_key="grid", type=EP_TYPE.SITE)

    # "homePower": 2594.19,
    HOMEPOWER = ApiKey(json_key="homePower", type=EP_TYPE.SITE)

    # -> NONE FREQUENT
    # POST /api/batterydischargecontrol/<status>: enable/disable battery discharge control (true/false)
    BATTERYDISCHARGECONTROL = ApiKey(json_key="batteryDischargeControl", type=EP_TYPE.SITE, writeable=True, write_key="batterydischargecontrol")

    # POST /api/residualpower/<power>: grid residual power in W
    RESIDUALPOWER = ApiKey(json_key="residualPower", type=EP_TYPE.SITE, writeable=True, write_key="residualpower")

    # POST /api/prioritysoc/<soc>: battery priority soc in %
    PRIORITYSOC = ApiKey(
        json_key="prioritySoc", type=EP_TYPE.SITE, writeable=True, write_key="prioritysoc", options=BATTERY_LIST
    )

    # POST /api/buffersoc/<soc>: battery buffer soc in %
    BUFFERSOC = ApiKey(
        json_key="bufferSoc", type=EP_TYPE.SITE, writeable=True, write_key="buffersoc", options=BATTERY_LIST[1:]
    )

    # POST /api/bufferstartsoc/<soc>: battery buffer start soc in %
    BUFFERSTARTSOC = ApiKey(
        json_key="bufferStartSoc", type=EP_TYPE.SITE, writeable=True, write_key="bufferstartsoc",
        options=BATTERY_LIST[1:]+BATTERY_LIST[0:1]
    )

    # when 'POST /api/smartcostlimit/<cost>:' smart charging cost limit (previously known as "cheap" tariff)
    # ALL smartCostLimit of all loadpoints will be set
    # SMARTCOSTLIMIT = ApiKey(json_key="smartCostLimit", type=EP_TYPE.SITE, writeable=True, write_key="smartcostlimit")

    AVAILABLEVERSION = ApiKey(json_key="availableVersion", type=EP_TYPE.SITE)

    VERSION = ApiKey(json_key="version", type=EP_TYPE.SITE)

    # "tariffGrid": 0.233835,
    TARIFFGRID = ApiKey(json_key="tariffGrid", type=EP_TYPE.SITE)

    # "tariffPriceHome": 0,
    TARIFFPRICEHOME = ApiKey(json_key="tariffPriceHome", type=EP_TYPE.SITE)

    # "tariffCo2": 197,
    TARIFFCO2 = ApiKey(json_key="tariffCo2", type=EP_TYPE.SITE)

    # "tariffCo2Home": 10.8131775758679,
    TARIFFCO2HOME = ApiKey(json_key="tariffCo2Home", type=EP_TYPE.SITE)

    # "tariffCo2Loadpoints": 197,
    TARIFFCO2LOADPOINTS = ApiKey(json_key="tariffCo2Loadpoints", type=EP_TYPE.SITE)

    # "tariffFeedIn": 0.078,
    TARIFFFEEDIN = ApiKey(json_key="tariffFeedIn", type=EP_TYPE.SITE)

    # "tariffPriceLoadpoints": 0.3584,
    TARIFFPRICELOADPOINTS = ApiKey(json_key="tariffPriceLoadpoints", type=EP_TYPE.SITE)

    # "tariffSolar": 595.829,
    TARIFFSOLAR = ApiKey(json_key="tariffSolar", type=EP_TYPE.SITE)

    # -> NONE FREQUENT
    # POST /api/batterydischargecontrol/<status>: enable/disable battery discharge control (true/false)
    # batteryGridChargeActive: false,
    BATTERYGRIDCHARGEACTIVE = ApiKey(json_key="batteryGridChargeActive", type=EP_TYPE.SITE, write_key="batterygridchargeactive")

    # batteryGridChargeLimit: ??
    BATTERYGRIDCHARGELIMIT = ApiKey(json_key="batteryGridChargeLimit", type=EP_TYPE.SITE, write_key="batterygridchargelimit")

    FORECAST_GRID = ApiKey(entity_key="forecast_grid", json_key="forecast", type=EP_TYPE.SITE)
    FORECAST_SOLAR = ApiKey(entity_key="forecast_solar", json_key="forecast", type=EP_TYPE.SITE)
    FORECAST_FEEDIN = ApiKey(entity_key="forecast_feedin", json_key="forecast", type=EP_TYPE.SITE)
    FORECAST_PLANNER = ApiKey(entity_key="forecast_planner", json_key="forecast", type=EP_TYPE.SITE)

    ###################################
    # CIRCUITS-DATA
    ###################################
    CIRCUITS_POWER = ApiKey(entity_key="circuits_power", json_key="power", type=EP_TYPE.CIRCUITS)
    CIRCUITS_CURRENT = ApiKey(entity_key="circuits_current", json_key="current", type=EP_TYPE.CIRCUITS)
    # CIRCUITS_MAXPOWER = ApiKey(entity_key="circuits_maxPower", json_key="maxPower", type=EP_TYPE.CIRCUITS)
    # CIRCUITS_MAXCURRENT = ApiKey(entity_key="circuits_maxCurrent", json_key="maxCurrent", type=EP_TYPE.CIRCUITS)
    CIRCUITS_DIMMED = ApiKey(entity_key="circuits_dimmed", json_key="dimmed", type=EP_TYPE.CIRCUITS)
    CIRCUITS_CURTAILED = ApiKey(entity_key="circuits_curtailed", json_key="curtailed", type=EP_TYPE.CIRCUITS)

    ###################################
    # LOADPOINT-DATA
    ###################################

    # "chargeCurrent": 0,
    # json_key_alias is a new property of a tag, that allows to specify a second json key
    # -> that is useful when an attribute will be renamed in the source API
    CHARGECURRENT = ApiKey(json_key="chargeCurrent", json_key_alias="offeredCurrent", type=EP_TYPE.LOADPOINTS)

    # "chargeCurrents": [0, 0, 0],
    CHARGECURRENTS = ApiKey(json_key="chargeCurrents", type=EP_TYPE.LOADPOINTS)

    # "chargeVoltages": [231.8800049, 232.8099976, 233.1199951],
    CHARGEVOLTAGES = ApiKey(json_key="chargeVoltages", type=EP_TYPE.LOADPOINTS)

    # "chargeDuration": 0, -> (in millis) ?! 840000000000 = 14min -> / 1000000
    CHARGEDURATION = ApiKey(json_key="chargeDuration", type=EP_TYPE.LOADPOINTS)
    CHARGEREMAININGDURATION = ApiKey(json_key="chargeRemainingDuration", type=EP_TYPE.LOADPOINTS)

    # "chargePower": 0,
    CHARGEPOWER = ApiKey(json_key="chargePower", type=EP_TYPE.LOADPOINTS)

    # "chargeTotalImport": 0.004,
    CHARGETOTALIMPORT = ApiKey(json_key="chargeTotalImport", type=EP_TYPE.LOADPOINTS)

    # "chargedEnergy": 0,
    CHARGEDENERGY = ApiKey(json_key="chargedEnergy", type=EP_TYPE.LOADPOINTS)
    CHARGEREMAININGENERGY = ApiKey(json_key="chargeRemainingEnergy", type=EP_TYPE.LOADPOINTS)

    # "chargerFeatureHeating": false,
    # "chargerFeatureIntegratedDevice": false,
    # "chargerIcon": null,
    # "chargerPhases1p3p": true,
    # "chargerPhysicalPhases": null,

    # "charging": false,
    CHARGING = ApiKey(json_key="charging", type=EP_TYPE.LOADPOINTS)

    # "connected": false,
    CONNECTED = ApiKey(json_key="connected", type=EP_TYPE.LOADPOINTS)

    # "connectedDuration": 9.223372036854776e+18,
    CONNECTEDDURATION = ApiKey(json_key="connectedDuration", type=EP_TYPE.LOADPOINTS)

    # "effectiveLimitSoc": 100,
    EFFECTIVELIMITSOC = ApiKey(json_key="effectiveLimitSoc", type=EP_TYPE.LOADPOINTS)

    # "effectiveMaxCurrent": 16,
    # "effectiveMinCurrent": 6,
    # "effectivePriority": 0,

    # "planActive": false,
    PLANACTIVE = ApiKey(json_key="planActive", type=EP_TYPE.LOADPOINTS)
    # this value is NOT present in the data - and must be calculated internally
    PLANACTIVEALT = ApiKey(json_key="planActiveAlt", type=EP_TYPE.LOADPOINTS)
    # "effectivePlanSoc": 0,
    EFFECTIVEPLANSOC = ApiKey(json_key="effectivePlanSoc", type=EP_TYPE.LOADPOINTS)
    # "effectivePlanTime": "0001-01-01T00:00:00Z",
    EFFECTIVEPLANTIME = ApiKey(json_key="effectivePlanTime", type=EP_TYPE.LOADPOINTS)
    # "planProjectedEnd": "2025-02-20T13:34:32+01:00",
    PLANPROJECTEDEND = ApiKey(json_key="planProjectedEnd", type=EP_TYPE.LOADPOINTS)
    # "planProjectedStart": "2025-02-20T13:00:00+01:00",
    PLANPROJECTEDSTART = ApiKey(json_key="planProjectedStart", type=EP_TYPE.LOADPOINTS)

    # "enabled": false,
    ENABLED = ApiKey(json_key="enabled", type=EP_TYPE.LOADPOINTS)

    # "phaseAction": "inactive",
    PHASEACTION = ApiKey(json_key="phaseAction", type=EP_TYPE.LOADPOINTS)

    # "phaseRemaining": 0,
    PHASEREMAINING = ApiKey(json_key="phaseRemaining", type=EP_TYPE.LOADPOINTS)

    # "phasesActive": 3,
    PHASESACTIVE = ApiKey(json_key="phasesActive", type=EP_TYPE.LOADPOINTS)

    # "phasesEnabled": 0,
    PHASESENABLED = ApiKey(json_key="phasesEnabled", type=EP_TYPE.LOADPOINTS)

    # "planOverrun": 0,
    PLANOVERRUN = ApiKey(json_key="planOverrun", type=EP_TYPE.LOADPOINTS)

    # "priority": 0,
    LPPRIORIRY = ApiKey(json_key="priority", write_key="priority", type=EP_TYPE.LOADPOINTS)

    # "pvAction": "inactive", "activ", "disable"
    PVACTION = ApiKey(json_key="pvAction", type=EP_TYPE.LOADPOINTS)
    # "pvRemaining": 0,
    PVREMAINING = ApiKey(json_key="pvRemaining", type=EP_TYPE.LOADPOINTS)
    # "enableDelay": 60,
    ENABLEDELAY = ApiKey(json_key="enableDelay", write_key="enable/delay", type=EP_TYPE.LOADPOINTS)
    # "disableDelay": 180,
    DISABLEDELAY = ApiKey(json_key="disableDelay", write_key="disable/delay", type=EP_TYPE.LOADPOINTS)

    # "sessionCo2PerKWh": null,
    SESSIONCO2PERKWH = ApiKey(json_key="sessionCo2PerKWh", type=EP_TYPE.LOADPOINTS)
    # "sessionEnergy": 0,
    SESSIONENERGY = ApiKey(json_key="sessionEnergy", type=EP_TYPE.LOADPOINTS)
    # "sessionPrice": null,
    SESSIONPRICE = ApiKey(json_key="sessionPrice", type=EP_TYPE.LOADPOINTS)
    # "sessionPricePerKWh": null,
    SESSIONPRICEPERKWH = ApiKey(json_key="sessionPricePerKWh", type=EP_TYPE.LOADPOINTS)
    # "sessionSolarPercentage": 0,
    SESSIONSOLARPERCENTAGE = ApiKey(json_key="sessionSolarPercentage", type=EP_TYPE.LOADPOINTS)

    # "smartCostActive": true,
    SMARTCOSTACTIVE = ApiKey(json_key="smartCostActive", type=EP_TYPE.LOADPOINTS)

    # "smartCostLimit": 0.22,
    SMARTCOSTLIMIT = ApiKey(json_key="smartCostLimit", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="smartcostlimit")

    # "title": "HH-7",
    # -> USED during startup phase

    # "vehicleClimaterActive": null,
    LP_VEHICLECLIMATERACTIVE = ApiKey(json_key="vehicleClimaterActive", type=EP_TYPE.LOADPOINTS)

    # "vehicleDetectionActive": false,
    LP_VEHICLEDETECTIONACTIVE = ApiKey(json_key="vehicleDetectionActive", type=EP_TYPE.LOADPOINTS)

    # start Vehicle Detection Button
    LP_DETECTVEHICLE = ApiKey(json_key="detectvehicle", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="detectvehicle")

    # "vehicleName": "",
    LP_VEHICLENAME = ApiKey(json_key="vehicleName", type=EP_TYPE.LOADPOINTS, writeable=True, write_key ="vehicle")

    # "vehicleOdometer": 0,
    LP_VEHICLEODOMETER = ApiKey(json_key="vehicleOdometer", type=EP_TYPE.LOADPOINTS)

    # "vehicleRange": 0,
    LP_VEHICLERANGE = ApiKey(json_key="vehicleRange", type=EP_TYPE.LOADPOINTS)

    # READ-ONLY Sensor
    # this is the limit configured for the car itself...
    # typically directly in the App of the vehicle vendor
    # in my personal case this is the FordPass App
    # It's a bit strange, that this field is not present
    # in the vehicle object of evcc?!
    # "vehicleLimitSoc": 100,
    LP_VEHICLELIMITSOC = ApiKey(json_key="vehicleLimitSoc", type=EP_TYPE.LOADPOINTS)

    # "vehicleSoc": 0
    LP_VEHICLESOC = ApiKey(json_key="vehicleSoc", type=EP_TYPE.LOADPOINTS)

    #"vehicleWelcomeActive": false
    LP_VEHICLEWELCOMEACTIVE = ApiKey(json_key="vehicleWelcomeActive", type=EP_TYPE.LOADPOINTS)

    # "mode": "off", -> (off/pv/minpv/now)
    MODE = ApiKey(
        json_key="mode", type=EP_TYPE.LOADPOINTS,
        writeable=True, write_key="mode", options=["off", "pv", "minpv", "now"]
    )
    # "limitSoc": 0, -> write 'limitsoc' in %
    LIMITSOC = ApiKey(json_key="limitSoc", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="limitsoc")

    # "limitEnergy": 0, -> write 'limitenergy' limit energy in kWh
    LIMITENERGY = ApiKey(json_key="limitEnergy", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="limitenergy")

    # "phasesConfigured": 0, -> write 'phases' -> allowed phases (0=auto/1=1p/3=3p)
    PHASES = ApiKey(json_key="phasesConfigured", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="phases", options=["0", "1", "3"])

    # "minCurrent": 6, -> write 'mincurrent' current minCurrent value in A
    MINCURRENT = ApiKey(json_key="minCurrent", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="mincurrent", options=MIN_CURRENT_LIST)

    # "maxCurrent": 16, -> write 'maxcurrent' current maxCurrent value in A
    MAXCURRENT = ApiKey(json_key="maxCurrent", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="maxcurrent", options=MAX_CURRENT_LIST)

    # enable/disable BatteryBoost (per Loadpoint)
    BATTERYBOOST = ApiKey(json_key="batteryBoost", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="batteryboost")

    # "disableThreshold": 0, -> write 'disable/threshold' (in W)
    DISABLETHRESHOLD = ApiKey(json_key="disableThreshold", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="disable/threshold")

    # "enableThreshold": 0, -> write 'enable/threshold' (in W)
    ENABLETHRESHOLD = ApiKey(json_key="enableThreshold", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="enable/threshold")

    # values can be written via SERVICE
    # "planEnergy": 0,
    PLANENERGY = ApiKey(json_key="planEnergy", type=EP_TYPE.LOADPOINTS)

    # "planTime": "0001-01-01T00:00:00Z",
    PLANTIME = ApiKey(json_key="planTime", type=EP_TYPE.LOADPOINTS)

    # delete plan button
    PLANDELETE = ApiKey(json_key="planDelete", type=EP_TYPE.LOADPOINTS, writeable=True, write_key="plan/energy")

    ###################################
    # VEHICLE
    ###################################

    # "vehicleLimitSoc": 0, -> write to vehicle EP!
    # even if we write to 'limitsoc' at the vehicle endpoint, the loadpoint[n]:vehicleLimitSoc values does not change ?!
    VEHICLELIMITSOC = ApiKey(json_key="limitSoc", type=EP_TYPE.VEHICLES, writeable=True, write_key="limitsoc", options=BATTERY_LIST)
    VEHICLEMINSOC = ApiKey(json_key="minSoc", type=EP_TYPE.VEHICLES, writeable=True, write_key="minsoc", options=BATTERY_LIST[:-1])

    # values can be written via SERVICE
    VEHICLEPLANSOC = ApiKey(json_key="vehiclePlansSoc", type=EP_TYPE.VEHICLES)
    VEHICLEPLANTIME = ApiKey(json_key="vehiclePlansTime", type=EP_TYPE.VEHICLES)
    # delete plan button
    VEHICLEPLANSDELETE= ApiKey(json_key="vehiclePlansDelete", type=EP_TYPE.VEHICLES, writeable=True, write_key="plan/soc")

    ###################################
    # STATISTICS
    ###################################

    STATTOTALAVGCO2 = ApiKey(entity_key="statTotalAvgCo2", json_key="avgCo2", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_TOTAL)
    STATTOTALAVGPRICE = ApiKey(entity_key="statTotalAvgPrice", json_key="avgPrice", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_TOTAL)
    STATTOTALCHARGEDKWH = ApiKey(entity_key="statTotalChargedKWh", json_key="chargedKWh", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_TOTAL)
    STATTOTALSOLARPERCENTAGE = ApiKey(entity_key="statTotalSolarPercentage", json_key="solarPercentage", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_TOTAL)

    STATTHISYEARAVGCO2 = ApiKey(entity_key="statThisYearAvgCo2", json_key="avgCo2", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_THISYEAR)
    STATTHISYEARAVGPRICE = ApiKey(entity_key="statThisYearAvgPrice", json_key="avgPrice", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_THISYEAR)
    STATTHISYEARCHARGEDKWH = ApiKey(entity_key="statThisYearChargedKWh", json_key="chargedKWh", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_THISYEAR)
    STATTHISYEARSOLARPERCENTAGE = ApiKey(entity_key="statThisYearSolarPercentage", json_key="solarPercentage", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_THISYEAR)

    STAT365AVGCO2 = ApiKey(entity_key="stat365AvgCo2", json_key="avgCo2", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_365D)
    STAT365AVGPRICE = ApiKey(entity_key="stat365AvgPrice", json_key="avgPrice", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_365D)
    STAT365CHARGEDKWH = ApiKey(entity_key="stat365ChargedKWh", json_key="chargedKWh", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_365D)
    STAT365SOLARPERCENTAGE = ApiKey(entity_key="stat365SolarPercentage", json_key="solarPercentage", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_365D)

    STAT30AVGCO2 = ApiKey(entity_key="stat30AvgCo2", json_key="avgCo2", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_30D)
    STAT30AVGPRICE = ApiKey(entity_key="stat30AvgPrice", json_key="avgPrice", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_30D)
    STAT30CHARGEDKWH = ApiKey(entity_key="stat30ChargedKWh", json_key="chargedKWh", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_30D)
    STAT30SOLARPERCENTAGE = ApiKey(entity_key="stat30SolarPercentage", json_key="solarPercentage", type=EP_TYPE.STATISTICS, subtype=JSONKEY_STATISTICS_30D)

    TARIFF_API_GRID = ApiKey(entity_key="tariff_api_grid", json_key="grid", type=EP_TYPE.TARIFF)
    TARIFF_API_SOLAR = ApiKey(entity_key="tariff_api_solar", json_key="solar", type=EP_TYPE.TARIFF)
    TARIFF_API_FEEDIN = ApiKey(entity_key="tariff_api_feedin", json_key="feedin", type=EP_TYPE.TARIFF)
    TARIFF_API_PLANNER = ApiKey(entity_key="tariff_api_planner", json_key="planner", type=EP_TYPE.TARIFF)

    CHARGING_SESSIONS = ApiKey(json_key="charging_sessions", type=EP_TYPE.SESSIONS)
    CHARGING_SESSIONS_VEHICLES = ApiKey(json_key="charging_sessions_vehicles", type=EP_TYPE.SESSIONS)
    CHARGING_SESSIONS_VEHICLE_COST = ApiKey(entity_key="charging_sessions_vehicle_cost", json_key="cost", type=EP_TYPE.SESSIONS, subtype=SESSIONS_KEY_VEHICLES)
    CHARGING_SESSIONS_VEHICLE_ENERGY = ApiKey(entity_key="charging_sessions_vehicle_chargedenergy", json_key="chargedEnergy", type=EP_TYPE.SESSIONS, subtype=SESSIONS_KEY_VEHICLES)
    CHARGING_SESSIONS_VEHICLE_DURATION = ApiKey(entity_key="charging_sessions_vehicle_chargeduration", json_key="chargeDuration", type=EP_TYPE.SESSIONS, subtype=SESSIONS_KEY_VEHICLES)

    CHARGING_SESSIONS_LOADPOINTS = ApiKey(json_key="charging_sessions_loadpoints", type=EP_TYPE.SESSIONS)
    CHARGING_SESSIONS_LOADPOINT_COST = ApiKey(entity_key="charging_sessions_loadpoint_cost", json_key="cost", type=EP_TYPE.SESSIONS, subtype=SESSIONS_KEY_LOADPOINTS)
    CHARGING_SESSIONS_LOADPOINT_ENERGY = ApiKey(entity_key="charging_sessions_loadpoint_chargedenergy", json_key="chargedEnergy", type=EP_TYPE.SESSIONS, subtype=SESSIONS_KEY_LOADPOINTS)
    CHARGING_SESSIONS_LOADPOINT_DURATION = ApiKey(entity_key="charging_sessions_loadpoint_chargeduration", json_key="chargeDuration", type=EP_TYPE.SESSIONS, subtype=SESSIONS_KEY_LOADPOINTS)

    ###################################
    # EV-OPTIMIZATION
    ###################################
    EVOPT_REQUEST_OBJECT = ApiKey(json_key=JSONKEY_EVOPT_REQ, type=EP_TYPE.EVOPT)
    EVOPT_RESULT_OBJECT = ApiKey(json_key=JSONKEY_EVOPT_RES, type=EP_TYPE.EVOPT)
    EVOPT_DETAILS_OBJECT = ApiKey(json_key=JSONKEY_EVOPT_DETAILS, type=EP_TYPE.EVOPT)