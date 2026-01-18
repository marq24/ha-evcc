from typing import Final

JSONKEY_PLANS_DEPRECATED: Final = "plans"
JSONKEY_PLAN: Final = "plan"
JSONKEY_PLAN_SOC: Final = "soc"
JSONKEY_PLAN_TIME: Final = "time"

JSONKEY_AUXPOWER: Final = "auxPower"
JSONKEY_CIRCUITS: Final = "circuits"
JSONKEY_LOADPOINTS: Final = "loadpoints"
JSONKEY_VEHICLES: Final = "vehicles"

JSONKEY_EVOPT: Final = "evopt"
JSONKEY_EVOPT_REQ: Final = "req"
JSONKEY_EVOPT_REQ_TIME_SERIES: Final = "time_series"
JSONKEY_EVOPT_REQ_TIME_SERIES_DT: Final = "dt"
JSONKEY_EVOPT_REQ_TIME_SERIES_FT: Final = "ft"
JSONKEY_EVOPT_REQ_TIME_SERIES_GT: Final = "gt"
JSONKEY_EVOPT_REQ_TIME_SERIES_PE: Final = "p_E"
JSONKEY_EVOPT_REQ_TIME_SERIES_PN: Final = "p_N"
JSONKEY_EVOPT_RES: Final = "res"
JSONKEY_EVOPT_RES_BATTERIES: Final = "batteries"
JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGING_POWER: Final = "charging_power"
JSONKEY_EVOPT_RES_BATTERIES_AINDEX_DISCHARGING_POWER: Final = "discharging_power"
# even this is named 'state_of_charge' in evcc - the 'value' IS the total amount or stored energy in the battery!
JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGED_TOTAL: Final = "state_of_charge"
JSONKEY_EVOPT_RES_FLOW_DIRECTION: Final = "flow_direction"
JSONKEY_EVOPT_RES_GRID_EXPORT: Final = "grid_export"
JSONKEY_EVOPT_RES_GRID_IMPORT: Final = "grid_import"
JSONKEY_EVOPT_RES_OBJECTIVE_VALUE: Final = "objective_value"
JSONKEY_EVOPT_RES_LIMIT_VIOLATIONS: Final = "limit_violations"
JSONKEY_EVOPT_RES_STATUS: Final = "status"
JSONKEY_EVOPT_DETAILS: Final = "details"
JSONKEY_EVOPT_DETAILS_TIMESTAMP: Final = "timestamp"
JSONKEY_EVOPT_DETAILS_BATTERYDETAILS: Final = "batteryDetails"

JSONKEY_BATTERYMODE: Final = "batteryMode"
JSONKEY_BATTERYPOWER: Final = "batteryPower"
#JSONKEY_BATTERYSOC: Final = "batterySoc"
JSONKEY_HOMEPOWER: Final = "homePower"
JSONKEY_PVENERGY: Final = "pvEnergy"
JSONKEY_PVPOWER: Final = "pvPower"
JSONKEY_PV: Final = "pv"
JSONKEY_STATISTICS: Final = "statistics"
JSONKEY_STATISTICS_TOTAL: Final = "total"
JSONKEY_STATISTICS_THISYEAR: Final = "thisYear"
JSONKEY_STATISTICS_365D: Final = "365d"
JSONKEY_STATISTICS_30D: Final = "30d"

JSONKEY_GRIDCURRENTS: Final = "gridCurrents"
JSONKEY_GRIDPOWER: Final = "gridPower"
JSONKEY_GRID: Final = "grid"

ADDITIONAL_ENDPOINTS_DATA_TARIFF: Final = "@@@tariff-data"
ADDITIONAL_ENDPOINTS_DATA_SESSIONS: Final = "@@@session-data"
SESSIONS_KEY_RAW: Final = "raw"
SESSIONS_KEY_TOTAL: Final = "total"
SESSIONS_KEY_VEHICLES: Final = "vehicles"
SESSIONS_KEY_LOADPOINTS: Final = "loadpoints"

# STATES: Final = [JSONKEY_LOADPOINTS, JSONKEY_AUXPOWER, JSONKEY_BATTERYMODE, JSONKEY_BATTERYPOWER, JSONKEY_BATTERYSOC,
#                  JSONKEY_GRID, JSONKEY_GRIDCURRENTS, JSONKEY_GRIDPOWER, JSONKEY_HOMEPOWER, JSONKEY_PVENERGY,
#                  JSONKEY_PVPOWER, JSONKEY_PV, JSONKEY_VEHICLES, JSONKEY_STATISTICS]

# FILTER_LOADPOINTS: Final = f"?jq=.{JSONKEY_LOADPOINTS}"

# STATE_QUERY = (
#     f"?jq={{{JSONKEY_LOADPOINTS}:.{JSONKEY_LOADPOINTS},{JSONKEY_AUXPOWER}:.{JSONKEY_AUXPOWER},{JSONKEY_BATTERYMODE}:.{JSONKEY_BATTERYMODE},{JSONKEY_BATTERYPOWER}:.{JSONKEY_BATTERYPOWER},{JSONKEY_BATTERYSOC}:.{JSONKEY_BATTERYSOC},{JSONKEY_GRID}:.{JSONKEY_GRID},{JSONKEY_GRIDCURRENTS}:.{JSONKEY_GRIDCURRENTS},{JSONKEY_GRIDPOWER}:.{JSONKEY_GRIDPOWER},{JSONKEY_HOMEPOWER}:.{JSONKEY_HOMEPOWER},{JSONKEY_HOMEPOWER}:.{JSONKEY_HOMEPOWER},{JSONKEY_PVENERGY}:.{JSONKEY_PVENERGY},{JSONKEY_PVPOWER}:.{JSONKEY_PVPOWER},{JSONKEY_PV}:.{JSONKEY_PV},{JSONKEY_VEHICLES}:.{JSONKEY_VEHICLES},{JSONKEY_STATISTICS}:.{JSONKEY_STATISTICS}}}"
# )

MIN_CURRENT_LIST: Final = ["0.125", "0.25", "0.5", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13",
                           "14", "15", "16"]#, "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32"]

MAX_CURRENT_LIST: Final = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17",
                           "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32",
                           "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47",
                           "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62",
                           "63", "64"]

BATTERY_LIST: Final = ["0", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75",
                       "80", "85", "90", "95", "100"]

TRANSLATIONS: Final = {
    "de": {
        "batterymode": {
            "unknown": "Unbekannt",
            "normal": "normal",
            "hold": "angehalten/gesperrt",
            "charge": "laden...",
        },
        "phaseaction":{
            "scale1p": "Reduziere auf einphasig",
            "scale3p": "Erhöhe auf dreiphasig",
            "inactive": "-keine-"
        },
        "pvaction":{
            "enable": "Ausreichend PV-Leistung vorhanden",
            "disable": "Unzureichende PV-Leistung, Aktivierung des Timeouts",
            "inactive": "Auch nach dem Timeout ist keine PV-Leistung verfügbar"
        },
        "device_name_loadpoint": "Ladepunkt",
        "device_name_vehicle": "Fahrzeug"
    },
    "en": {
        "batterymode": {
            "unknown": "unknown",
            "normal": "normal",
            "hold": "on-hold",
            "charge": "charging...",
        },
        "phaseaction":{
            "scale1p": "Reducing to 1-phase charging",
            "scale3p": "Increasing to 3-phase charging",
            "inactive": "-none-"
        },
        "pvaction":{
            "enable": "Sufficient PV power available",
            "disable": "Insufficient PV power, activating the timeout",
            "inactive": "No PV power available even after the timeout"
        },
        "device_name_loadpoint": "Loadpoint",
        "device_name_vehicle": "Vehicle"
    }
}
