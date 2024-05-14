import logging
from enum import Enum
from typing import (
    NamedTuple, Final, Callable
)

# from aenum import Enum, extend_enum

_LOGGER: logging.Logger = logging.getLogger(__package__)

IS_TRIGGER: Final = "TRIGGER"

class CAT(Enum):
    CONFIG = "CONF"
    STATUS = "STAT"
    OTHER = "OTHE"
    CONSTANT = "CONS"

class ENDPOINT_TYPE(Enum):
    LOADPOINT = "loadpoint"
    VEHICLE = "vehicle"
    SITE = "site"

class ApiKey(NamedTuple):

    # def _decode_value_default(self, src_value):
    #     _LOGGER.debug(f"reading TAG {self.key} from {src_value}")
    #     pass
    #
    # def _encode_value_default(self):
    #     pass
    #
    # def _decode_mode(self, src_value):
    #     # possible mode strings: off/pv/minpv/now
    #     if isinstance(src_value, str):
    #         src_value = src_value.lower()
    #         if "off" == src_value:
    #             return 0
    #         elif "pv" == src_value:
    #             return 1
    #         elif "minpv" == src_value:
    #             return 2
    #         elif "now" == src_value:
    #             return 3
    #         else:
    #             return None
    #
    # def _encode_mode(self, src_value):
    #     match int(src_value):
    #         case 0:
    #             return "off"
    #         case 1:
    #             return "pv"
    #         case 2:
    #             return "minpv"
    #         case 3:
    #             return "now"
    #     return None

    key: str
    write_key: str
    type: str
    writeable: bool = False
    writeonly: bool = False
    #decode_f: Callable = _decode_value_default
    #encode_f: Callable = _encode_value_default

# see https://github.com/goecharger/go-eCharger-API-v2/blob/main/apikeys-en.md for details
class Tag(ApiKey, Enum):

    def __hash__(self) -> int:
        return hash(self.key)

    def __str__(self):
        return self.key

# "chargeCurrent": 0,
# "chargeCurrents": [0, 0, 0],
# "chargeDuration": 0,
# "chargePower": 0,
# "chargeTotalImport": 0.004,
# "chargedEnergy": 0,
# "chargerFeatureHeating": false,
# "chargerFeatureIntegratedDevice": false,
# "chargerIcon": null,
# "chargerPhases1p3p": true,
# "chargerPhysicalPhases": null,
# "charging": false,
# "connected": false,
# "connectedDuration": 9.223372036854776e+18,
# "effectiveLimitSoc": 100,
# "effectiveMaxCurrent": 16,
# "effectiveMinCurrent": 6,
# "effectivePlanSoc": 0,
# "effectivePlanTime": "0001-01-01T00:00:00Z",
# "effectivePriority": 0,
# "enabled": false,
# "phaseAction": "inactive",
# "phaseRemaining": 0,
# "phasesActive": 3,
# "phasesEnabled": 0,
# "planEnergy": 0,
# "planOverrun": 0,
# "planProjectedStart": "0001-01-01T00:00:00Z",
# "planTime": "0001-01-01T00:00:00Z",
# "priority": 0,
# "pvAction": "inactive",
# "pvRemaining": 0,
# "sessionCo2PerKWh": null,
# "sessionEnergy": 0,
# "sessionPrice": null,
# "sessionPricePerKWh": null,
# "sessionSolarPercentage": 0,
# "smartCostActive": true,
# "smartCostLimit": 0.22,
# "title": "HH-7",
# "vehicleClimaterActive": null,
# "vehicleDetectionActive": false,
# "vehicleLimitSoc": 0,
# "vehicleName": "",
# "vehicleOdometer": 0,
# "vehicleRange": 0,
# "vehicleSoc": 0

    # "mode": "off", -> (off/pv/minpv/now)
    # "limitSoc": 0, -> write 'limitsoc' in %
    # "limitEnergy": 0, -> write 'limitenergy' limit energy in kWh
    # "phasesConfigured": 0, -> write 'phases' -> allowed phases (0=auto/1=1p/3=3p)
    # "minCurrent": 6, -> write 'mincurrent' current minCurrent value in A
    # "maxCurrent": 16, -> write 'maxcurrent' current maxCurrent value in A
    # "disableThreshold": 0, -> write 'disable/threshold' (in W)
    # "enableThreshold": 0, -> write 'enable/threshold' (in W)

    MODE = ApiKey(key="mode", write_key="mode", type=ENDPOINT_TYPE.LOADPOINT, writeable=True)
    LIMITSOC = ApiKey(key="limitSoc", write_key="limitsoc", type=ENDPOINT_TYPE.LOADPOINT, writeable=True)
    LIMITENERGY = ApiKey(key="limitEnergy", write_key="limitenergy", type=ENDPOINT_TYPE.LOADPOINT, writeable=True)
    PHASES = ApiKey(key="phasesConfigured", write_key="phases", type=ENDPOINT_TYPE.LOADPOINT, writeable=True)
    MINCURRENT = ApiKey(key="minCurrent", write_key="mincurrent", type=ENDPOINT_TYPE.LOADPOINT, writeable=True)
    MAXCURRENT = ApiKey(key="maxCurrent", write_key="maxcurrent", type=ENDPOINT_TYPE.LOADPOINT, writeable=True)
    DISABLETHRESHOLD = ApiKey(key="disableThreshold", write_key="disable/threshold", type=ENDPOINT_TYPE.LOADPOINT, writeable=True)
    ENABLETHRESHOLD = ApiKey(key="enableThreshold", write_key="enable/threshold", type=ENDPOINT_TYPE.LOADPOINT, writeable=True)