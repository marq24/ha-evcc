from dataclasses import dataclass
from typing import Final

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.number import NumberEntityDescription, NumberMode, NumberDeviceClass
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass, SensorDeviceClass
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfTime,
    PERCENTAGE
)
from homeassistant.util.frozen_dataclass_compat import FrozenOrThawed

from custom_components.evcc_intg.pyevcc_ha.keys import Tag

# Base component constants
MANUFACTURER: Final = "marq24: evcc HACS Integration (unofficial)"
NAME: Final = "evcc Bridge (unofficial)"
DOMAIN: Final = "evcc_intg"
ISSUE_URL: Final = "https://github.com/marq24/ha-evcc/issues"

STARTUP_MESSAGE: Final = f"""
-------------------------------------------------------------------
{NAME}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""


SERVICE_SET_LOADPOINT_PLAN: Final = "set_loadpoint_plan"
SERVICE_SET_VEHICLE_PLAN: Final = "set_vehicle_plan"

@dataclass
class EntityDescriptionStub(metaclass=FrozenOrThawed, frozen_or_thawed=True):
    tag: Tag = None,
    icon: str | None = None
    device_class: str | None = None
    unit_of_measurement: str | None = None
    entity_category: EntityCategory | None = None
    entity_registry_enabled_default: bool = True

@dataclass
class ExtBinarySensorEntityDescriptionStub(EntityDescriptionStub):
    icon_off: str | None = None


@dataclass
class ExtBinarySensorEntityDescription(BinarySensorEntityDescription):
    tag: Tag = None
    idx: int | None = None
    name_addon: str | None = None

    icon_off: str | None = None

@dataclass
class ExtButtonEntityDescriptionStub(EntityDescriptionStub):
    payload: str | None = None


@dataclass
class ExtButtonEntityDescription(ButtonEntityDescription):
    tag: Tag = None
    idx: int | None = None
    name_addon: str | None = None

    payload: str | None = None


@dataclass
class ExtNumberEntityDescriptionStub(EntityDescriptionStub):
    max_value: None = None
    min_value: None = None
    mode: NumberMode | None = None
    native_max_value: float | None = None
    native_min_value: float | None = None
    native_step: float | None = None
    native_unit_of_measurement: str | None = None
    step: None = None


@dataclass
class ExtNumberEntityDescription(NumberEntityDescription):
    tag: Tag = None
    idx: int | None = None
    name_addon: str | None = None


@dataclass
class ExtSelectEntityDescriptionStub(EntityDescriptionStub):
    options: list[str] | None = None,


@dataclass
class ExtSelectEntityDescription(SelectEntityDescription):
    tag: Tag = None
    idx: int | None = None
    name_addon: str | None = None


@dataclass
class ExtSensorEntityDescriptionStub(EntityDescriptionStub):
    state_class: SensorStateClass | str | None = None
    suggested_display_precision: int | None = None
    native_unit_of_measurement: str | None = None
    array_idx: int | None = None
    factor: int | None = None


@dataclass
class ExtSensorEntityDescription(SensorEntityDescription):
    tag: Tag = None
    idx: int | None = None
    name_addon: str | None = None
    array_idx: int | None = None
    factor: int | None = None

@dataclass
class ExtSwitchEntityDescriptionStub(EntityDescriptionStub):
    icon_off: str | None = None


@dataclass
class ExtSwitchEntityDescription(SwitchEntityDescription):
    tag: Tag = None
    idx: int | None = None
    name_addon: str | None = None
    icon_off: str | None = None


PLATFORMS: Final = ["binary_sensor", "button", "number", "select", "sensor", "switch"]

BINARY_SENSORS = []
BINARY_SENSORS_PER_LOADPOINT = [
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.CHARGING,
        icon=None,
        icon_off=None
    ),
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.CONNECTED,
        icon=None,
        icon_off=None
    ),
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.ENABLED,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon=None,
        icon_off=None
    ),
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.SMARTCOSTACTIVE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon=None,
        icon_off=None
    ),
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.VEHICLEDETECTIONACTIVE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:car-search",
        icon_off="mdi:car-search-outline"
    )
]

BUTTONS = []
BUTTONS_PER_LOADPOINT = [
    ExtButtonEntityDescriptionStub(
        tag=Tag.VEHICLEPLANSDELETE,
        entity_category=EntityCategory.CONFIG,
        device_class=None,
        icon="mdi:restart"
    ),
    ExtButtonEntityDescriptionStub(
        tag=Tag.PLANDELETE,
        entity_category=EntityCategory.CONFIG,
        device_class=None,
        icon="mdi:restart",
        entity_registry_enabled_default=False
    ),
    ExtButtonEntityDescriptionStub(
        tag=Tag.DETECTVEHICLE,
        device_class=None,
        icon="mdi:car-search-outline"
    ),
]

NUMBER_SENSORS = [
    ExtNumberEntityDescription(
        tag=Tag.RESIDUALPOWER,
        key=Tag.RESIDUALPOWER.key,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:home-lightning-bolt-outline",
        mode = NumberMode.BOX,
        native_max_value=10000,
        native_min_value=-500,
        native_step=50,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class= NumberDeviceClass.POWER,
    ),
]
NUMBER_SENSORS_PER_LOADPOINT = [
    ExtNumberEntityDescriptionStub(
        tag=Tag.LIMITSOC,
        icon="mdi:battery-charging",
        mode = NumberMode.SLIDER,
        native_max_value=100,
        native_min_value=20,
        native_step=5,
        device_class= NumberDeviceClass.BATTERY,
    ),
    ExtNumberEntityDescriptionStub(
        tag=Tag.ENABLETHRESHOLD,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:scale-balance",
        mode = NumberMode.BOX,
        native_max_value=10000,
        native_min_value=-500,
        native_step=50,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class= NumberDeviceClass.POWER,
    ),
    ExtNumberEntityDescriptionStub(
        tag=Tag.DISABLETHRESHOLD,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:scale-balance",
        mode = NumberMode.BOX,
        native_max_value=10000,
        native_min_value=-500,
        native_step=50,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class= NumberDeviceClass.POWER,
    ),
    ExtNumberEntityDescriptionStub(
        tag=Tag.LIMITENERGY,
        icon="mdi:lightning-bolt-outline",
        mode = NumberMode.BOX,
        native_max_value=200,
        native_min_value=0,
        native_step=1,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False
    ),
    ExtNumberEntityDescriptionStub(
        tag=Tag.SMARTCOSTLIMIT,
        entity_category=EntityCategory.CONFIG,
        icon = "mdi:cash-multiple",
        mode = NumberMode.BOX,
        native_max_value=20.00,
        native_min_value=0.00,
        native_step=0.01,
        native_unit_of_measurement="@@@/kWh",
    )
]

SELECT_SENSORS = [
    ExtSelectEntityDescription(
        tag=Tag.PRIORITYSOC,
        key=Tag.PRIORITYSOC.key,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:home-battery-outline",
        options=Tag.PRIORITYSOC.options
        # we render the states via translations - so we can render '0 %' as '---'
        #unit_of_measurement=PERCENTAGE,
        #device_class= NumberDeviceClass.BATTERY,
    ),
    ExtSelectEntityDescription(
        tag=Tag.BUFFERSOC,
        key=Tag.BUFFERSOC.key,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:home-battery-outline",
        options=Tag.BUFFERSOC.options
        # we render the states via translations - so we can render '0 %' as '---'
        #unit_of_measurement=PERCENTAGE,
        #device_class= NumberDeviceClass.BATTERY,
    ),
    ExtSelectEntityDescription(
        tag=Tag.BUFFERSTARTSOC,
        key=Tag.BUFFERSTARTSOC.key,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:home-battery-outline",
        options=Tag.BUFFERSTARTSOC.options
        # we render the states via translations - so we can render '0 %' as '---'
        #unit_of_measurement=PERCENTAGE,
        #device_class= NumberDeviceClass.BATTERY,
    )
]
SELECT_SENSORS_PER_LOADPOINT = [
    ExtSelectEntityDescriptionStub(
        tag=Tag.MODE,
        #entity_category=EntityCategory.CONFIG,
        icon="mdi:state-machine"
    ),
    ExtSelectEntityDescriptionStub(
        tag=Tag.PHASES,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:lightning-bolt-outline"
    ),
    ExtSelectEntityDescriptionStub(
        tag=Tag.VEHICLENAME,
        #entity_category=EntityCategory.CONFIG,
        icon="mdi:car-outline"
    ),
    ExtSelectEntityDescriptionStub(
        tag=Tag.MINCURRENT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:current-ac",
        unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=NumberDeviceClass.CURRENT,
    ),
    ExtSelectEntityDescriptionStub(
        tag=Tag.MAXCURRENT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:current-ac",
        unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=NumberDeviceClass.CURRENT,
    ),
    ExtSelectEntityDescriptionStub(
        tag=Tag.VEHICLELIMITSOC,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:battery-charging",
        # we render the states via translations - so we can render '0 %' as '---'
        #unit_of_measurement=PERCENTAGE,
        #device_class= NumberDeviceClass.BATTERY,
    ),
    ExtSelectEntityDescriptionStub(
        tag=Tag.VEHICLEMINSOC,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:battery-charging",
        # we render the states via translations - so we can render '0 %' as '---'
        #unit_of_measurement=PERCENTAGE,
        #device_class= NumberDeviceClass.BATTERY,
    )
]

SENSOR_SENSORS = []
SENSOR_SENSORS_PER_LOADPOINT = [

    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGECURRENT,
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGECURRENTS,
        array_idx=0,
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGECURRENTS,
        array_idx=1,
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGECURRENTS,
        array_idx=2,
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEDURATION,
        icon="mdi:clock-digital",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        factor = 60000000000,
        #factor = 60000000,
        device_class=SensorDeviceClass.DURATION,
        suggested_display_precision=0
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEREMAININGDURATION,
        icon="mdi:clock-digital",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        factor = 60000000000,
        suggested_display_precision=0
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEPOWER,
        icon="mdi:meter-electric-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        factor=1000,
        suggested_display_precision=2
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGETOTALIMPORT,
        icon="mdi:transmission-tower-export",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        device_class=None
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEDENERGY,
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        factor=1000,
        suggested_display_precision=2
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEREMAININGENERGY,
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        factor=1000,
        suggested_display_precision=2
    ),

    # ExtSensorEntityDescriptionStub(
    #     tag=Tag.CONNECTEDDURATION,
    #     icon="mdi:clock-digital",
    #     state_class=SensorStateClass.MEASUREMENT,
    #     native_unit_of_measurement=UnitOfTime.MICROSECONDS,
    #     unit_of_measurement=UnitOfTime.MINUTES,
    #     device_class=None
    # ),

    ExtSensorEntityDescriptionStub(
        tag=Tag.PHASEACTION,
        icon="mdi:numeric",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        device_class=None
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PHASEREMAINING,
        icon="mdi:numeric",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        device_class=None
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PHASESACTIVE,
        icon="mdi:numeric",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        device_class=None
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PHASESENABLED,
        icon="mdi:numeric",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        device_class=None
    ),

    ExtSensorEntityDescriptionStub(
        tag=Tag.SESSIONCO2PERKWH,
        icon="mdi:molecule-co2",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="CO₂/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.SESSIONENERGY,
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        factor=1000,
        suggested_display_precision=2
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.SESSIONPRICE,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=3
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.SESSIONPRICEPERKWH,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.SESSIONSOLARPERCENTAGE,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0
    ),

    ExtSensorEntityDescriptionStub(
        tag=Tag.VEHICLERANGE,
        icon="mdi:ev-station",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=None,
        suggested_display_precision=0
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.VEHICLESOC,
        icon="mdi:car-electric-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0
    ),

    ExtSensorEntityDescriptionStub(
        tag=Tag.VEHICLEPLANSSOC,
        icon="mdi:battery-charging",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.VEHICLEPLANSTIME,
        icon="mdi:calendar-arrow-right",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATE
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PLANENERGY,
        icon="mdi:battery-charging",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PLANTIME,
        icon="mdi:calendar-arrow-right",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATE,
        entity_registry_enabled_default=False
    ),
]
# SENSOR_SENSORS = [
#     # INDEXED Values...
#     # nrg
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=0,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricPotential.VOLT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.VOLTAGE,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=1,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricPotential.VOLT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.VOLTAGE,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=2,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricPotential.VOLT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.VOLTAGE,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=3,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricPotential.VOLT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.VOLTAGE,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=4,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.CURRENT,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=5,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.CURRENT,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=6,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.CURRENT,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=7,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=8,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=9,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=10,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=11,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=12,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=PERCENTAGE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER_FACTOR,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=13,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=PERCENTAGE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER_FACTOR,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=14,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=PERCENTAGE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER_FACTOR,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.NRG.key,
#         idx=15,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=PERCENTAGE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER_FACTOR,
#         entity_registry_enabled_default=True
#     ),
#     # tma
#     ExtSensorEntityDescription(
#         key=Tag.TMA.key,
#         idx=0,
#         suggested_display_precision=1,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTemperature.CELSIUS,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.TEMPERATURE,
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.TMA.key,
#         idx=1,
#         suggested_display_precision=1,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTemperature.CELSIUS,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.TEMPERATURE,
#         entity_registry_enabled_default=True
#     ),
#
#     # cdi -> object
#     ExtSensorEntityDescription(
#         key=Tag.CDI.key,
#         idx="type",
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:counter",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.CDI.key,
#         idx="value",
#         factor=60000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.MINUTES,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=True
#     ),
#     # atp -> object [NOT IMPLEMENTED YET]
#     # TODO:HERE
#     # ExtSensorEntityDescription(
#     #     key=Tag.ATP.key,
#     #     idx="???",
#     #     entity_category=EntityCategory.DIAGNOSTIC,
#     #     native_unit_of_measurement=None,
#     #     state_class=SensorStateClass.MEASUREMENT,
#     #     device_class=None,
#     #     icon="mdi:mdi:bug-outline",
#     #     entity_registry_enabled_default=False
#     # ),
#     # awcp -> object
#     ExtSensorEntityDescription(
#         key=Tag.AWCP.key,
#         idx="marketprice",
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=CURRENCY_CENT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:cash",
#         entity_registry_enabled_default=False
#     ),
#     # ccu -> object [not testable yet] - But looks like this is only the progress for
#     # the update -> so we will ignore it for now!
#     # TODO:HERE
#     # ExtSensorEntityDescription(
#     #     key=Tag.CCU.key,
#     #     idx="",
#     #     entity_category=EntityCategory.DIAGNOSTIC,
#     #     native_unit_of_measurement=None,
#     #     state_class=SensorStateClass.MEASUREMENT,
#     #     device_class=None,
#     #     icon="mdi:gauge",
#     #     entity_registry_enabled_default=False
#     # ),
#     # ccw -> object
#     ExtSensorEntityDescription(
#         key=Tag.CCW.key,
#         idx="ssid",
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:wifi",
#         entity_registry_enabled_default=False
#     ),
#
#     # LOOKUP-Values [always two Sensors!]
#     # car
#     # cus
#     # err
#     # modelstatus
#     # ffb
#     # frm
#     # lck
#     # pwm
#     # wsms
#     # wst
#     ExtSensorEntityDescription(
#         key=Tag.CAR.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:state-machine",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.CAR.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:state-machine",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.CUS.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:lock-question",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.CUS.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:lock-question",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.ERR.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:alert-circle-outline",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.ERR.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:alert-circle-outline",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.MODELSTATUS.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:state-machine",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.MODELSTATUS.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:state-machine",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.FFB.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:lock-open-check-outline",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.FFB.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:lock-open-check-outline",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.FRM.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:transmission-tower-export",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.FRM.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:transmission-tower-export",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.LCK.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:lock-open-alert-outline",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.LCK.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:lock-open-alert-outline",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.PWM.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:bug-outline",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.PWM.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:bug-outline",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.WSMS.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:wifi-settings",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.WSMS.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:wifi-settings",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.WST.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:wifi",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.WST.key,
#         lookup=True,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=None,
#         device_class=None,
#         icon="mdi:wifi",
#         entity_registry_enabled_default=True
#     ),
#
#     # TIMES from here...
#     # fsptws
#     # inva
#     # lbp
#     # lccfc
#     # lccfi
#     # lcctc
#     # lfspt
#     # lmsc
#     # lpsc
#     # rbt
#     ExtSensorEntityDescription(
#         key=Tag.FSPTWS.key,
#         factor=60000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.MINUTES,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.INVA.key,
#         factor=1000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.SECONDS,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.LBP.key,
#         factor=60000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.MINUTES,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:button-pointer",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.LCCFC.key,
#         factor=60000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.MINUTES,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.LCCFI.key,
#         factor=60000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.MINUTES,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.LCCTC.key,
#         factor=60000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.MINUTES,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.LFSPT.key,
#         factor=60000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.MINUTES,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=False
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.LMSC.key,
#         factor=1000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.SECONDS,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.LPSC.key,
#         factor=1000,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.SECONDS,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.RBT.key,
#         factor=3600000, # time in full hours!
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTime.HOURS,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:timer-outline",
#         entity_registry_enabled_default=True
#     ),
#
#     # So finally the normal sensor here...
#     # acu
#     ExtSensorEntityDescription(
#         key=Tag.ACU.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.CURRENT,
#         entity_registry_enabled_default=True
#     ),
#     # amt
#     ExtSensorEntityDescription(
#         key=Tag.AMT.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfTemperature.CELSIUS,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.TEMPERATURE,
#         entity_registry_enabled_default=True
#     ),
#     # cbl
#     ExtSensorEntityDescription(
#         key=Tag.CBL.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.CURRENT,
#         entity_registry_enabled_default=False
#     ),
#     # deltaa
#     ExtSensorEntityDescription(
#         key=Tag.DELTAA.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.CURRENT,
#         entity_registry_enabled_default=False
#     ),
#     # deltap
#     ExtSensorEntityDescription(
#         key=Tag.DELTAP.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         entity_registry_enabled_default=False
#     ),
#     # eto
#     ExtSensorEntityDescription(
#         key=Tag.ETO.key,
#         factor=1000,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
#         state_class=SensorStateClass.TOTAL_INCREASING,
#         device_class=SensorDeviceClass.ENERGY,
#         icon="mdi:lightning-bolt",
#         entity_registry_enabled_default=True
#     ),
#     # ferm
#     # NOT-AVAILABLE in MY DATA ?!
#     # TODO:HERE!
#
#     # fhz
#     ExtSensorEntityDescription(
#         key=Tag.FHZ.key,
#         suggested_display_precision=3,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfFrequency.HERTZ,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:current-ac",
#         entity_registry_enabled_default=False
#     ),
#     # loa
#     ExtSensorEntityDescription(
#         key=Tag.LOA.key,
#         name="Load balancing available current",
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.CURRENT,
#         entity_registry_enabled_default=True
#     ),
#     # map
#     ExtSensorEntityDescription(
#         key=Tag.MAP.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:vector-triangle",
#         entity_registry_enabled_default=True
#     ),
#     # mmp
#     ExtSensorEntityDescription(
#         key=Tag.MMP.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         icon="mdi:bug-outline",
#         entity_registry_enabled_default=True
#     ),
#     # nif
#     ExtSensorEntityDescription(
#         key=Tag.NIF.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:navigation-variant-outline",
#         entity_registry_enabled_default=False
#     ),
#     # pakku
#     ExtSensorEntityDescription(
#         key=Tag.PAKKU.key,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         icon="mdi:home-battery-outline",
#         entity_registry_enabled_default=True
#     ),
#     # pgrid
#     ExtSensorEntityDescription(
#         key=Tag.PGRID.key,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         icon="mdi:transmission-tower-export",
#         entity_registry_enabled_default=True
#     ),
#     # pnp
#     ExtSensorEntityDescription(
#         key=Tag.PNP.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         icon="mdi:counter",
#         entity_registry_enabled_default=False
#     ),
#     # ppv
#     ExtSensorEntityDescription(
#         key=Tag.PPV.key,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         icon="mdi:solar-power",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.PVOPT_AVERAGEPAKKU.key,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         icon="mdi:home-battery-outline",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.PVOPT_AVERAGEPGRID.key,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         icon="mdi:transmission-tower-export",
#         entity_registry_enabled_default=True
#     ),
#     ExtSensorEntityDescription(
#         key=Tag.PVOPT_AVERAGEPPV.key,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         icon="mdi:solar-power",
#         entity_registry_enabled_default=True
#     ),
#     # rbc
#     ExtSensorEntityDescription(
#         key=Tag.RBC.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=SensorStateClass.TOTAL_INCREASING,
#         device_class=None,
#         icon="mdi:counter",
#         entity_registry_enabled_default=True
#     ),
#     # rfb
#     ExtSensorEntityDescription(
#         key=Tag.RFB.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=None,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=None,
#         entity_registry_enabled_default=False
#     ),
#     # rssi
#     ExtSensorEntityDescription(
#         key=Tag.RSSI.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.SIGNAL_STRENGTH,
#         icon="mdi:wifi-strength-2",
#         entity_registry_enabled_default=True
#     ),
#     # tpa
#     ExtSensorEntityDescription(
#         key=Tag.TPA.key,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfPower.WATT,
#         state_class=SensorStateClass.MEASUREMENT,
#         device_class=SensorDeviceClass.POWER,
#         entity_registry_enabled_default=True
#     ),
#     # wh
#     ExtSensorEntityDescription(
#         key=Tag.WH.key,
#         factor=1000,
#         suggested_display_precision=2,
#         entity_category=EntityCategory.DIAGNOSTIC,
#         native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
#         state_class=SensorStateClass.TOTAL_INCREASING,
#         icon="mdi:lightning-bolt",
#         device_class=SensorDeviceClass.ENERGY,
#         entity_registry_enabled_default=True
#     ),
#     # wsc -> later (if at all)
#     # wsm -> later (if at all)
#
# ]

SWITCH_SENSORS = [
    ExtSwitchEntityDescription(
        tag=Tag.BATTERYDISCHARGECONTROL,
        key=Tag.BATTERYDISCHARGECONTROL.key,
        icon="mdi:battery-off-outline",
        entity_category=EntityCategory.CONFIG,
        device_class=None
    ),
]
SWITCH_SENSORS_PER_LOADPOINT = []