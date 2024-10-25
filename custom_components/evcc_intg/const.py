from dataclasses import dataclass
from typing import Final

from custom_components.evcc_intg.pyevcc_ha.keys import Tag
from homeassistant.components.binary_sensor import BinarySensorEntityDescription, BinarySensorDeviceClass
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

# Base component constants
MANUFACTURER: Final = "marq24 [not connected with the evcc.io team]"
NAME: Final = "evcc☀️🚘- Solar Charging"
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

CONF_INCLUDE_EVCC: Final = "include_evcc"

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
    suggested_unit_of_measurement: str | None = None
    suggested_display_precision: int | None = None
    native_unit_of_measurement: str | None = None

    array_idx: int | None = None
    factor: int | None = None
    lookup: bool | None = None

@dataclass
class ExtSensorEntityDescription(SensorEntityDescription):
    tag: Tag = None
    idx: int | None = None
    name_addon: str | None = None

    array_idx: int | None = None
    factor: int | None = None
    lookup: bool | None = None

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

BINARY_SENSORS = [
    ExtBinarySensorEntityDescription(
        tag=Tag.BATTERYGRIDCHARGEACTIVE,
        key=Tag.BATTERYGRIDCHARGEACTIVE.key,
        icon="mdi:battery-charging-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=None
    ),
]
BINARY_SENSORS_PER_LOADPOINT = [
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.CHARGING,
        icon=None,
        icon_off=None,
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING
    ),
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.CONNECTED,
        icon=None,
        icon_off=None,
        device_class=BinarySensorDeviceClass.CONNECTIVITY
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
        native_max_value=25000,
        native_min_value=-5000,
        native_step=50,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
    ),
    ExtNumberEntityDescription(
        tag=Tag.BATTERYGRIDCHARGELIMIT,
        key=Tag.BATTERYGRIDCHARGELIMIT.key,
        entity_category=EntityCategory.CONFIG,
        icon = "mdi:cash-multiple",
        mode = NumberMode.BOX,
        native_max_value=0.45,
        native_min_value=-0.05,
        native_step=0.005,
        native_unit_of_measurement="@@@/kWh"
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
        native_unit_of_measurement=PERCENTAGE,
        device_class= NumberDeviceClass.BATTERY,
    ),
    ExtNumberEntityDescriptionStub(
        tag=Tag.ENABLETHRESHOLD,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:scale-balance",
        mode = NumberMode.BOX,
        native_max_value=25000,
        native_min_value=-5000,
        native_step=50,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class= NumberDeviceClass.POWER,
    ),
    ExtNumberEntityDescriptionStub(
        tag=Tag.DISABLETHRESHOLD,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:scale-balance",
        mode = NumberMode.BOX,
        native_max_value=25000,
        native_min_value=-5000,
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
        native_max_value=0.45,
        native_min_value=-0.05,
        native_step=0.005,
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

SENSOR_SENSORS = [
    ExtSensorEntityDescription(
        tag=Tag.AUXPOWER,
        key=Tag.AUXPOWER.key,
        icon="mdi:home-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERYMODE,
        key=f"{Tag.BATTERYMODE.key}_value",
        icon="mdi:state-machine",
        lookup=True
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERYMODE,
        key=f"{Tag.BATTERYMODE.key}",
        icon="mdi:state-machine",
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERYPOWER,
        key=Tag.BATTERYPOWER.key,
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERYSOC,
        key=Tag.BATTERYSOC.key,
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRIDCURRENTS,
        key=f"{Tag.GRIDCURRENTS.key}_0",
        array_idx=0,
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRIDCURRENTS,
        key=f"{Tag.GRIDCURRENTS.key}_1",
        array_idx=1,
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRIDCURRENTS,
        key=f"{Tag.GRIDCURRENTS.key}_2",
        array_idx=2,
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRIDPOWER,
        key=Tag.GRIDPOWER.key,
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER
    ),
    ExtSensorEntityDescription(
        tag=Tag.HOMEPOWER,
        key=Tag.HOMEPOWER.key,
        icon="mdi:home-lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER
    ),
    ExtSensorEntityDescription(
        tag=Tag.PVPOWER,
        key=Tag.PVPOWER.key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER
    ),

    ExtSensorEntityDescription(
        tag=Tag.BATTERYCAPACITY,
        key=Tag.BATTERYCAPACITY.key,
        icon="mdi:battery",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=1
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFFGRID,
        key=Tag.TARIFFGRID.key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFFPRICEHOME,
        key=Tag.TARIFFPRICEHOME.key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@/kWh",
        device_class=None,
        suggested_display_precision=3
    ),

    ExtSensorEntityDescription(
        tag=Tag.STATTOTALSOLARPERCENTAGE,
        key=Tag.STATTOTALSOLARPERCENTAGE.entity_key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=4
    ),
    ExtSensorEntityDescription(
        tag=Tag.STATTOTALCHARGEDKWH,
        key=Tag.STATTOTALCHARGEDKWH.entity_key,
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=4
    ),
    ExtSensorEntityDescription(
        tag=Tag.STATTOTALAVGPRICE,
        key=Tag.STATTOTALAVGPRICE.entity_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=4
    ),
    ExtSensorEntityDescription(
        tag=Tag.STATTOTALAVGCO2,
        key=Tag.STATTOTALAVGCO2.entity_key,
        icon="mdi:molecule-co2",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="CO₂",
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STATTHISYEARSOLARPERCENTAGE,
        key=Tag.STATTHISYEARSOLARPERCENTAGE.entity_key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STATTHISYEARCHARGEDKWH,
        key=Tag.STATTHISYEARCHARGEDKWH.entity_key,
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STATTHISYEARAVGPRICE,
        key=Tag.STATTHISYEARAVGPRICE.entity_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STATTHISYEARAVGCO2,
        key=Tag.STATTHISYEARAVGCO2.entity_key,
        icon="mdi:molecule-co2",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="CO₂",
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STAT365SOLARPERCENTAGE,
        key=Tag.STAT365SOLARPERCENTAGE.entity_key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STAT365CHARGEDKWH,
        key=Tag.STAT365CHARGEDKWH.entity_key,
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STAT365AVGPRICE,
        key=Tag.STAT365AVGPRICE.entity_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STAT365AVGCO2,
        key=Tag.STAT365AVGCO2.entity_key,
        icon="mdi:molecule-co2",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="CO₂",
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STAT30SOLARPERCENTAGE,
        key=Tag.STAT30SOLARPERCENTAGE.entity_key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STAT30CHARGEDKWH,
        key=Tag.STAT30CHARGEDKWH.entity_key,
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STAT30AVGPRICE,
        key=Tag.STAT30AVGPRICE.entity_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.STAT30AVGCO2,
        key=Tag.STAT30AVGCO2.entity_key,
        icon="mdi:molecule-co2",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="CO₂",
        device_class=None,
        suggested_display_precision=4,
        entity_registry_enabled_default=False
    )
]
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
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        suggested_display_precision=0
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEREMAININGDURATION,
        icon="mdi:clock-digital",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
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
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEDENERGY,
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        factor=1000,
        suggested_display_precision=2
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEREMAININGENERGY,
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.TOTAL,
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
        state_class=None,
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PHASEACTION,
        lookup=True,
        icon="mdi:numeric",
        state_class=None,
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM
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
        state_class=SensorStateClass.TOTAL_INCREASING,
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
        tag=Tag.VEHICLEODOMETER,
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
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
        #state_class=SensorStateClass.MEASUREMENT,
        #device_class=SensorDeviceClass.DATE,
        device_class=None
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
        #state_class=SensorStateClass.MEASUREMENT,
        #device_class=SensorDeviceClass.DATE,
        device_class=None,
        entity_registry_enabled_default=False
    ),
]

SWITCH_SENSORS = [
    ExtSwitchEntityDescription(
        tag=Tag.BATTERYDISCHARGECONTROL,
        key=Tag.BATTERYDISCHARGECONTROL.key,
        icon="mdi:battery-off-outline",
        entity_category=EntityCategory.CONFIG,
        device_class=None
    )
]
SWITCH_SENSORS_PER_LOADPOINT = []