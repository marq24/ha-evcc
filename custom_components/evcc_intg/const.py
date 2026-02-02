from dataclasses import dataclass
from typing import Final

from custom_components.evcc_intg.pyevcc_ha.const import (
    JSONKEY_EVOPT_RES_BATTERIES,
    JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGING_POWER,
    JSONKEY_EVOPT_RES_BATTERIES_AINDEX_DISCHARGING_POWER,
    JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGED_TOTAL,
    JSONKEY_EVOPT_REQ_TIME_SERIES,
    JSONKEY_EVOPT_REQ_TIME_SERIES_DT,
)
from custom_components.evcc_intg.pyevcc_ha.keys import Tag, GRID_CONTENT, PV_CONTENT, FORECAST_CONTENT, BATTERY_CONTENT
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
    UnitOfElectricPotential,
    PERCENTAGE,
    Platform
)

# Base component constants
MANUFACTURER: Final = "marq24"
NAME: Final = "evcc ☀️🚘 Solar Charging"
NAME_SHORT: Final = "evcc"
DOMAIN: Final = "evcc_intg"
ISSUE_URL: Final = "https://github.com/marq24/ha-evcc/issues"

CONFIG_VERSION: Final = 2
CONFIG_MINOR_VERSION: Final = 0

STARTUP_MESSAGE: Final = f"""
-------------------------------------------------------------------
{NAME} - v%s
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

CONF_INCLUDE_EVCC: Final = "include_evcc"
CONF_PURGE_ALL: Final = "purge_all_devices"
CONF_USE_WS= "use_websocket"

EVCC_JSON_KEY_NAME: Final = "evccName"
EVCC_JSON_ORIGIN_OBJECT = "originObject"

SERVICE_SET_LOADPOINT_PLAN: Final = "set_loadpoint_plan"
SERVICE_SET_VEHICLE_PLAN: Final = "set_vehicle_plan"
SERVICE_DEL_LOADPOINT_PLAN: Final = "del_loadpoint_plan"
SERVICE_DEL_VEHICLE_PLAN: Final = "del_vehicle_plan"

# Map tags to their content keys
TAG_TO_CONTENT_KEY: Final = {
    Tag.FORECAST_GRID: FORECAST_CONTENT.GRID.value,
    Tag.FORECAST_FEEDIN: FORECAST_CONTENT.FEEDIN.value,
    Tag.FORECAST_PLANNER: FORECAST_CONTENT.PLANNER.value,
}

@dataclass(frozen=True)
class EntityDescriptionStub():
    tag: Tag = None,
    icon: str | None = None
    device_class: str | None = None
    unit_of_measurement: str | None = None
    entity_category: EntityCategory | None = None
    entity_registry_enabled_default: bool = True
    integrated_supported: bool = True


@dataclass(frozen=True)
class ExtBinarySensorEntityDescriptionStub(EntityDescriptionStub):
    icon_off: str | None = None

@dataclass(frozen=True)
class ExtBinarySensorEntityDescription(BinarySensorEntityDescription):
    tag: Tag = None
    lp_idx: int | str | None = None
    name_addon: str | None = None

    icon_off: str | None = None


@dataclass(frozen=True)
class ExtButtonEntityDescriptionStub(EntityDescriptionStub):
    payload: str | None = None

@dataclass(frozen=True)
class ExtButtonEntityDescription(ButtonEntityDescription):
    tag: Tag = None
    lp_idx: int | str | None = None
    name_addon: str | None = None

    payload: str | None = None


@dataclass(frozen=True)
class ExtNumberEntityDescriptionStub(EntityDescriptionStub):
    max_value: None = None
    min_value: None = None
    mode: NumberMode | None = None
    native_max_value: float | None = None
    native_min_value: float | None = None
    native_step: float | None = None
    native_unit_of_measurement: str | None = None
    step: None = None

@dataclass(frozen=True)
class ExtNumberEntityDescription(NumberEntityDescription):
    tag: Tag = None
    lp_idx: int | str | None = None
    name_addon: str | None = None


@dataclass(frozen=True)
class ExtSelectEntityDescriptionStub(EntityDescriptionStub):
    options: list[str] | None = None,

@dataclass(frozen=True)
class ExtSelectEntityDescription(SelectEntityDescription):
    tag: Tag = None
    lp_idx: int | str | None = None
    name_addon: str | None = None


@dataclass(frozen=True)
class ExtSensorEntityDescriptionStub(EntityDescriptionStub):
    state_class: SensorStateClass | str | None = None
    suggested_unit_of_measurement: str | None = None
    suggested_display_precision: int | None = None
    native_unit_of_measurement: str | None = None

    json_idx: list[str|int] | None = None
    factor: int | None = None
    lookup: bool | None = None
    ignore_zero: bool | None = None

@dataclass(frozen=True)
class ExtSensorEntityDescription(SensorEntityDescription):
    tag: Tag = None
    lp_idx: int | str | None = None
    name_addon: str | None = None

    json_idx: list[str|int] | None = None
    factor: int | None = None
    lookup: bool | None = None
    ignore_zero: bool | None = None


@dataclass(frozen=True)
class ExtSwitchEntityDescriptionStub(EntityDescriptionStub):
    icon_off: str | None = None

@dataclass(frozen=True)
class ExtSwitchEntityDescription(SwitchEntityDescription):
    tag: Tag = None
    lp_idx: int | str | None = None
    name_addon: str | None = None

    icon_off: str | None = None

PLATFORMS: Final = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

BINARY_ENTITIES = [
    ExtBinarySensorEntityDescription(
        tag=Tag.BATTERYGRIDCHARGEACTIVE,
        key=Tag.BATTERYGRIDCHARGEACTIVE.json_key,
        icon="mdi:battery-charging-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=None
    ),
]
BINARY_ENTITIES_PER_CIRCUIT = [
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.CIRCUITS_DIMMED,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower-off",
        icon_off="mdi:transmission-tower",
    ),
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.CIRCUITS_CURTAILED,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower-off",
        icon_off="mdi:transmission-tower",
        entity_registry_enabled_default=False
    ),
]
BINARY_ENTITIES_PER_LOADPOINT = [
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
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        integrated_supported=False
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
        tag=Tag.LP_VEHICLEDETECTIONACTIVE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:car-search",
        icon_off="mdi:car-search-outline",
        integrated_supported=False
    ),
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.LP_VEHICLECLIMATERACTIVE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan",
        icon_off="mdi:fan-off",
        integrated_supported=False
    ),
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.LP_VEHICLEWELCOMEACTIVE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:gift-outline",
        icon_off="mdi:gift-off-outline",
        integrated_supported=False
    ),
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.PLANACTIVE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-clock",
        icon_off="mdi:calendar-blank",
    ),
    # for what ever reason, the 'PLANACTIVE' api value is sometimes false, while the plan is already
    # activated in evcc (and the 'effectivePlanTime' is already set - so this can be used as fallback)
    ExtBinarySensorEntityDescriptionStub(
        tag=Tag.PLANACTIVEALT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-check",
        icon_off="mdi:calendar-blank",
        entity_registry_enabled_default=False
    )
]

BUTTONS_ENTITIES = []
BUTTONS_ENTITIES_PER_LOADPOINT = [
    ExtButtonEntityDescriptionStub(
        tag=Tag.VEHICLEPLANSDELETE,
        entity_category=EntityCategory.CONFIG,
        device_class=None,
        icon="mdi:restart",
        integrated_supported = False
    ),
    ExtButtonEntityDescriptionStub(
        tag=Tag.PLANDELETE,
        entity_category=EntityCategory.CONFIG,
        device_class=None,
        icon="mdi:restart",
        entity_registry_enabled_default=False,
        integrated_supported = False
    ),
    ExtButtonEntityDescriptionStub(
        tag=Tag.LP_DETECTVEHICLE,
        device_class=None,
        icon="mdi:car-search-outline",
        integrated_supported = False
    ),
    ExtButtonEntityDescriptionStub(
        tag=Tag.SMARTCOSTLIMIT,
        entity_category=EntityCategory.CONFIG,
        device_class=None,
        icon = "mdi:cash-off",
        entity_registry_enabled_default=False,
        integrated_supported = False
    )
]

NUMBER_ENTITIES = [
    ExtNumberEntityDescription(
        tag=Tag.RESIDUALPOWER,
        key=Tag.RESIDUALPOWER.json_key,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:home-lightning-bolt-outline",
        mode = NumberMode.BOX,
        native_max_value=25000,
        native_min_value=-25000,
        native_step=50,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
    ),
    ExtNumberEntityDescription(
        tag=Tag.BATTERYGRIDCHARGELIMIT,
        key=Tag.BATTERYGRIDCHARGELIMIT.json_key,
        entity_category=EntityCategory.CONFIG,
        icon = "mdi:cash-multiple",
        mode = NumberMode.BOX,
        native_max_value=2.50,
        native_min_value=-0.05,
        native_step=0.005,
        native_unit_of_measurement="@@@/kWh"
    ),
]
NUMBER_ENTITIES_PER_LOADPOINT = [
    ExtNumberEntityDescriptionStub(
        tag=Tag.LIMITSOC,
        icon="mdi:battery-charging",
        mode = NumberMode.SLIDER,
        native_max_value=100,
        native_min_value=20,
        native_step=5,
        native_unit_of_measurement=PERCENTAGE,
        device_class= NumberDeviceClass.BATTERY,
        #integrated_supported=False
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
        native_max_value=2.50,
        native_min_value=-0.05,
        native_step=0.005,
        native_unit_of_measurement="@@@/kWh",
    ),
    ExtNumberEntityDescriptionStub(
        tag=Tag.ENABLEDELAY,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:weather-sunset-up",
        mode = NumberMode.BOX,
        native_max_value=6000,
        native_min_value=0,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    ExtNumberEntityDescriptionStub(
        tag=Tag.DISABLEDELAY,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:weather-sunset-down",
        mode = NumberMode.BOX,
        native_max_value=6000,
        native_min_value=0,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    ExtNumberEntityDescriptionStub(
        tag=Tag.LPPRIORIRY,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:priority-high",
        mode = NumberMode.SLIDER,
        native_max_value=10,
        native_min_value=0,
        native_step=1,
        device_class=None
    ),
]

SELECT_ENTITIES = [
    ExtSelectEntityDescription(
        tag=Tag.PRIORITYSOC,
        key=Tag.PRIORITYSOC.json_key,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:home-battery-outline",
        options=Tag.PRIORITYSOC.options
        # we render the states via translations - so we can render '0 %' as '---'
        #unit_of_measurement=PERCENTAGE,
        #device_class= NumberDeviceClass.BATTERY,
    ),
    ExtSelectEntityDescription(
        tag=Tag.BUFFERSOC,
        key=Tag.BUFFERSOC.json_key,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:home-battery-outline",
        options=Tag.BUFFERSOC.options
        # we render the states via translations - so we can render '0 %' as '---'
        #unit_of_measurement=PERCENTAGE,
        #device_class= NumberDeviceClass.BATTERY,
    ),
    ExtSelectEntityDescription(
        tag=Tag.BUFFERSTARTSOC,
        key=Tag.BUFFERSTARTSOC.json_key,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:home-battery-outline",
        options=Tag.BUFFERSTARTSOC.options
        # we render the states via translations - so we can render '0 %' as '---'
        #unit_of_measurement=PERCENTAGE,
        #device_class= NumberDeviceClass.BATTERY,
    )
]
SELECT_ENTITIES_PER_LOADPOINT = [
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
        tag=Tag.LP_VEHICLENAME,
        #entity_category=EntityCategory.CONFIG,
        icon="mdi:car-outline",
        integrated_supported=False
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
        integrated_supported=False
    ),
    ExtSelectEntityDescriptionStub(
        tag=Tag.VEHICLEMINSOC,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:battery-charging",
        # we render the states via translations - so we can render '0 %' as '---'
        #unit_of_measurement=PERCENTAGE,
        #device_class= NumberDeviceClass.BATTERY,
        integrated_supported=False
    )
]

SENSOR_ENTITIES_GRID_AS_PREFIX = [
    ExtSensorEntityDescription(
        tag=Tag.GRIDPOWER,
        key=Tag.GRIDPOWER.json_key,
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.POWER
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRIDCURRENTS,
        key=f"{Tag.GRIDCURRENTS.json_key}_0",
        json_idx=[0],
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRIDCURRENTS,
        key=f"{Tag.GRIDCURRENTS.json_key}_1",
        json_idx=[1],
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRIDCURRENTS,
        key=f"{Tag.GRIDCURRENTS.json_key}_2",
        json_idx=[2],
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    )
]
SENSOR_ENTITIES_GRID_AS_OBJECT = [
    ExtSensorEntityDescription(
        tag=Tag.GRID,
        key=Tag.GRIDPOWER.json_key, # we keep here the KEY from the GRID_AS_PREFIX_SENSORS!
        json_idx=[GRID_CONTENT.POWER.value],
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.POWER
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRID,
        key=f"{Tag.GRIDCURRENTS.json_key}_0", # we keep here the KEY from the GRID_AS_PREFIX_SENSORS!
        json_idx=[GRID_CONTENT.CURRENTS.value, 0],
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRID,
        key=f"{Tag.GRIDCURRENTS.json_key}_1", # we keep here the KEY from the GRID_AS_PREFIX_SENSORS!
        json_idx=[GRID_CONTENT.CURRENTS.value, 1],
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.GRID,
        key=f"{Tag.GRIDCURRENTS.json_key}_2", # we keep here the KEY from the GRID_AS_PREFIX_SENSORS!
        json_idx=[GRID_CONTENT.CURRENTS.value, 2],
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
]
SENSOR_ENTITIES_BATTERY_AS_PREFIX = [
    ExtSensorEntityDescription(
        tag=Tag.BATTERYPOWER,
        key=Tag.BATTERYPOWER.json_key,
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY,
        key="battery_0_power",
        json_idx=[0, BATTERY_CONTENT.POWER.value],
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY,
        key="battery_1_power",
        json_idx=[1, BATTERY_CONTENT.POWER.value],
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY,
        key="battery_2_power",
        json_idx=[2, BATTERY_CONTENT.POWER.value],
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY,
        key="battery_3_power",
        json_idx=[3, BATTERY_CONTENT.POWER.value],
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),

    ExtSensorEntityDescription(
        tag=Tag.BATTERYSOC,
        key=Tag.BATTERYSOC.json_key,
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY,
        key="battery_0_soc",
        json_idx=[0, BATTERY_CONTENT.SOC.value],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY,
        key="battery_1_soc",
        json_idx=[1, BATTERY_CONTENT.SOC.value],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY,
        key="battery_2_soc",
        json_idx=[2, BATTERY_CONTENT.SOC.value],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY,
        key="battery_3_soc",
        json_idx=[3, BATTERY_CONTENT.SOC.value],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        entity_registry_enabled_default=False
    ),

    ExtSensorEntityDescription(
        tag=Tag.BATTERYCAPACITY,
        key=Tag.BATTERYCAPACITY.json_key,
        icon="mdi:battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=1
    ),
]
SENSOR_ENTITIES_BATTERY_AS_OBJECT = [
    ExtSensorEntityDescription(
        tag=Tag.BATTERYPOWER_AS_OBJ,
        key=Tag.BATTERYPOWER_AS_OBJ.entity_key,
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY_AS_OBJ,
        key="battery_0_power",
        json_idx=[0, BATTERY_CONTENT.POWER.value],
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY_AS_OBJ,
        key="battery_1_power",
        json_idx=[1, BATTERY_CONTENT.POWER.value],
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY_AS_OBJ,
        key="battery_2_power",
        json_idx=[2, BATTERY_CONTENT.POWER.value],
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY_AS_OBJ,
        key="battery_3_power",
        json_idx=[3, BATTERY_CONTENT.POWER.value],
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),

    ExtSensorEntityDescription(
        tag=Tag.BATTERYSOC_AS_OBJ,
        key=Tag.BATTERYSOC_AS_OBJ.entity_key,
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY_AS_OBJ,
        key="battery_0_soc",
        json_idx=[0, BATTERY_CONTENT.SOC.value],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY_AS_OBJ,
        key="battery_1_soc",
        json_idx=[1, BATTERY_CONTENT.SOC.value],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY_AS_OBJ,
        key="battery_2_soc",
        json_idx=[2, BATTERY_CONTENT.SOC.value],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERY_AS_OBJ,
        key="battery_3_soc",
        json_idx=[3, BATTERY_CONTENT.SOC.value],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        entity_registry_enabled_default=False
    ),

    ExtSensorEntityDescription(
        tag=Tag.BATTERYCAPACITY_AS_OBJ,
        key=Tag.BATTERYCAPACITY_AS_OBJ.entity_key,
        icon="mdi:battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=1
    ),
]
SENSOR_ENTITIES = [
    ExtSensorEntityDescription(
        tag=Tag.AUXPOWER,
        key=Tag.AUXPOWER.json_key,
        icon="mdi:home-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERYMODE,
        key=f"{Tag.BATTERYMODE.json_key}_value",
        icon="mdi:state-machine",
        lookup=True
    ),
    ExtSensorEntityDescription(
        tag=Tag.BATTERYMODE,
        key=Tag.BATTERYMODE.json_key,
        icon="mdi:state-machine",
        entity_registry_enabled_default=False
    ),

    ExtSensorEntityDescription(
        tag=Tag.HOMEPOWER,
        key=Tag.HOMEPOWER.json_key,
        icon="mdi:home-lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.POWER
    ),
    ExtSensorEntityDescription(
        tag=Tag.PVENERGY,
        key=Tag.PVENERGY.json_key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
    ),
    ExtSensorEntityDescription(
        tag=Tag.PV,
        key="pv_0_energy",
        json_idx=[0, PV_CONTENT.ENERGY.value],
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.PV,
        key="pv_1_energy",
        json_idx=[1, PV_CONTENT.ENERGY.value],
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.PV,
        key="pv_2_energy",
        json_idx=[2, PV_CONTENT.ENERGY.value],
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.PV,
        key="pv_3_energy",
        json_idx=[3, PV_CONTENT.ENERGY.value],
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.PVPOWER,
        key=Tag.PVPOWER.json_key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
    ),
    ExtSensorEntityDescription(
        tag=Tag.PV,
        key="pv_0_power",
        json_idx=[0, PV_CONTENT.POWER.value],
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.PV,
        key="pv_1_power",
        json_idx=[1, PV_CONTENT.POWER.value],
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.PV,
        key="pv_2_power",
        json_idx=[2, PV_CONTENT.POWER.value],
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.PV,
        key="pv_3_power",
        json_idx=[3, PV_CONTENT.POWER.value],
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFFGRID,
        key=Tag.TARIFFGRID.json_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFFPRICEHOME,
        key=Tag.TARIFFPRICEHOME.json_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    # ---------------------
    ExtSensorEntityDescription(
        tag=Tag.TARIFFCO2,
        key=Tag.TARIFFCO2.json_key,
        icon="mdi:molecule-co2",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="g/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFFCO2HOME,
        key=Tag.TARIFFCO2HOME.json_key,
        icon="mdi:molecule-co2",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="g/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFFCO2LOADPOINTS,
        key=Tag.TARIFFCO2LOADPOINTS.json_key,
        icon="mdi:molecule-co2",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="g/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    # ---------------------
    ExtSensorEntityDescription(
        tag=Tag.TARIFFFEEDIN,
        key=Tag.TARIFFFEEDIN.json_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFFPRICELOADPOINTS,
        key=Tag.TARIFFPRICELOADPOINTS.json_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@/kWh",
        device_class=None,
        suggested_display_precision=3
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFFSOLAR,
        key=Tag.TARIFFSOLAR.json_key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=None,
        suggested_display_precision=2,
    ),
    ExtSensorEntityDescription(
        tag=Tag.STATTOTALSOLARPERCENTAGE,
        key=Tag.STATTOTALSOLARPERCENTAGE.entity_key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=2
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
        suggested_display_precision=2,
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
        suggested_display_precision=2,
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
        suggested_display_precision=2,
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
    ),

    # the new tarif endpoints... [GRID & SOLAR]
    ExtSensorEntityDescription(
        tag=Tag.TARIFF_API_GRID,
        key=Tag.TARIFF_API_GRID.entity_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=3,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFF_API_SOLAR,
        key=Tag.TARIFF_API_SOLAR.entity_key,
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=None,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFF_API_FEEDIN,
        key=Tag.TARIFF_API_FEEDIN.entity_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=3,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.TARIFF_API_PLANNER,
        key=Tag.TARIFF_API_PLANNER.entity_key,
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=3,
        entity_registry_enabled_default=False
    ),

    # the new forecast endpoints... [GRID & SOLAR]
    ExtSensorEntityDescription(
        tag=Tag.FORECAST_GRID,
        key=Tag.FORECAST_GRID.entity_key,
        json_idx=[FORECAST_CONTENT.GRID.value],
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=3,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.FORECAST_SOLAR,
        key=Tag.FORECAST_SOLAR.entity_key,
        json_idx=[FORECAST_CONTENT.SOLAR.value],
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=None,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.FORECAST_FEEDIN,
        key=Tag.FORECAST_FEEDIN.entity_key,
        json_idx=[FORECAST_CONTENT.FEEDIN.value],
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=3,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.FORECAST_PLANNER,
        key=Tag.FORECAST_PLANNER.entity_key,
        json_idx=[FORECAST_CONTENT.PLANNER.value],
        icon="mdi:cash-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=3,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.CHARGING_SESSIONS,
        key=Tag.CHARGING_SESSIONS.json_key,
        icon="mdi:chart-box-multiple-outline",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription(
        tag=Tag.CHARGING_SESSIONS_VEHICLES,
        key=Tag.CHARGING_SESSIONS_VEHICLES.json_key,
        icon="mdi:chart-box-outline",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.CHARGING_SESSIONS_LOADPOINTS,
        key=Tag.CHARGING_SESSIONS_LOADPOINTS.json_key,
        icon="mdi:chart-box-outline",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False
    ),

    # OPTIMIZER SENSORS
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_REQUEST_OBJECT,
        key="evopt_time_series_dt",
        json_idx=[JSONKEY_EVOPT_REQ_TIME_SERIES, JSONKEY_EVOPT_REQ_TIME_SERIES_DT, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_RESULT_OBJECT,
        key="evopt_battery_0_charging_power",
        json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 0, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGING_POWER, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_RESULT_OBJECT,
        key="evopt_battery_0_discharging_power",
        json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 0, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_DISCHARGING_POWER, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_RESULT_OBJECT,
        key="evopt_battery_0_charged_total",
        json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 0, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGED_TOTAL, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_RESULT_OBJECT,
        key="evopt_battery_1_charging_power",
        json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 1, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGING_POWER, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_RESULT_OBJECT,
        key="evopt_battery_1_discharging_power",
        json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 1, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_DISCHARGING_POWER, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_RESULT_OBJECT,
        key="evopt_battery_1_charged_total",
        json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 1, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGED_TOTAL, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_RESULT_OBJECT,
        key="evopt_battery_2_charging_power",
        json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 2, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGING_POWER, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_RESULT_OBJECT,
        key="evopt_battery_2_discharging_power",
        json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 2, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_DISCHARGING_POWER, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescription(
        tag=Tag.EVOPT_RESULT_OBJECT,
        key="evopt_battery_2_charged_total",
        json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 2, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGED_TOTAL, 0],
        icon="mdi:home-battery-outline",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False
    ),
]
SENSOR_ENTITIES_PER_LOADPOINT = [

    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGECURRENT,
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGECURRENTS,
        json_idx=[0],
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGECURRENTS,
        json_idx=[1],
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGECURRENTS,
        json_idx=[2],
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),


    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEVOLTAGES,
        json_idx=[0],
        suggested_display_precision=2,
        icon="mdi:lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEVOLTAGES,
        json_idx=[1],
        suggested_display_precision=2,
        icon="mdi:lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGEVOLTAGES,
        json_idx=[2],
        suggested_display_precision=2,
        icon="mdi:lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
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
        tag=Tag.EFFECTIVELIMITSOC,
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        #integrated_supported=False
    ),
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
        native_unit_of_measurement="g/kWh",
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
        tag=Tag.LP_VEHICLELIMITSOC,
        icon="mdi:battery-charging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.LP_VEHICLEODOMETER,
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=None,
        suggested_display_precision=0,
        ignore_zero=True,
        integrated_supported=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.LP_VEHICLERANGE,
        icon="mdi:ev-station",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=None,
        suggested_display_precision=0,
        integrated_supported=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.LP_VEHICLESOC,
        icon="mdi:car-electric-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        suggested_display_precision=0,
        #integrated_supported=False - requested in https://github.com/marq24/ha-evcc/issues/157
    ),

    ExtSensorEntityDescriptionStub(
        tag=Tag.VEHICLEPLANSOC,
        icon="mdi:battery-charging",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        integrated_supported=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.VEHICLEPLANTIME,
        icon="mdi:calendar-arrow-right",
        entity_category=EntityCategory.DIAGNOSTIC,
        #state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        #device_class=None,
        integrated_supported=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PLANENERGY,
        icon="mdi:battery-charging",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PLANTIME,
        icon="mdi:calendar-arrow-right",
        entity_category=EntityCategory.DIAGNOSTIC,
        #state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        #device_class=None,
        entity_registry_enabled_default=False
    ),

    ExtSensorEntityDescriptionStub(
        tag=Tag.EFFECTIVEPLANTIME,
        icon="mdi:calendar-arrow-right",
        entity_category=EntityCategory.DIAGNOSTIC,
        #state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        #device_class=None,
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PLANPROJECTEDSTART,
        icon="mdi:calendar-start",
        entity_category=EntityCategory.DIAGNOSTIC,
        #state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        #device_class=None,
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PLANPROJECTEDEND,
        icon="mdi:calendar-end",
        entity_category=EntityCategory.DIAGNOSTIC,
        #state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        #device_class=None,
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.EFFECTIVEPLANSOC,
        icon="mdi:battery-charging",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        #integrated_supported=False
    ),

    ExtSensorEntityDescriptionStub(
        tag=Tag.PVACTION,
        lookup=True,
        icon="mdi:state-machine",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PVACTION,
        icon="mdi:state-machine",
        state_class=None,
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.PVREMAINING,
        icon="mdi:sun-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        #state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        #device_class=None,
    ),

    # charging session sensors's per LOADPOINT
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGING_SESSIONS_LOADPOINT_ENERGY,
        icon="mdi:lightning-bolt-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=True
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGING_SESSIONS_LOADPOINT_COST,
        icon="mdi:cash-multiple",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=3,
        entity_registry_enabled_default=True
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGING_SESSIONS_LOADPOINT_DURATION,
        icon="mdi:clock-digital",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        suggested_display_precision=1,
        entity_registry_enabled_default=True
    ),
]
SENSOR_ENTITIES_PER_VEHICLE = [
    # charging session sensors's per VEHICLE
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGING_SESSIONS_VEHICLE_ENERGY,
        icon="mdi:lightning-bolt-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=True
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGING_SESSIONS_VEHICLE_COST,
        icon="mdi:cash-multiple",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="@@@",
        device_class=None,
        suggested_display_precision=3,
        entity_registry_enabled_default=True
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CHARGING_SESSIONS_VEHICLE_DURATION,
        icon="mdi:clock-digital",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        suggested_display_precision=1,
        entity_registry_enabled_default=True
    ),
]
SENSOR_ENTITIES_PER_CIRCUIT = [
    ExtSensorEntityDescriptionStub(
        tag=Tag.CIRCUITS_POWER,
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False
    ),
    ExtSensorEntityDescriptionStub(
        tag=Tag.CIRCUITS_CURRENT,
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False
    ),
    # ExtSensorEntityDescriptionStub(
    #     tag=Tag.GRID,
    #     icon="mdi:current-ac",
    #     state_class=SensorStateClass.MEASUREMENT,
    #     native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    #     device_class=SensorDeviceClass.CURRENT,
    #     entity_registry_enabled_default=False
    # ),
    # ExtSensorEntityDescriptionStub(
    #     tag=Tag.GRID,
    #     icon="mdi:current-ac",
    #     state_class=SensorStateClass.MEASUREMENT,
    #     native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    #     device_class=SensorDeviceClass.CURRENT,
    #     entity_registry_enabled_default=False
    # ),
]

# SENSOR_SENSORS_PER_VEHICLE = [
#
#     ExtSensorEntityDescriptionStub(
#         tag=Tag.VEHOBJ_LIMITSOC,
#         icon="mdi:battery-charging",
#         state_class=SensorStateClass.MEASUREMENT,
#         native_unit_of_measurement=PERCENTAGE,
#         device_class=None,
#         suggested_display_precision=0,
#     ),
#     ExtSensorEntityDescriptionStub(
#         tag=Tag.VEHOBJ_MINSOC,
#         icon="mdi:car-electric-outline",
#         state_class=SensorStateClass.MEASUREMENT,
#         native_unit_of_measurement=PERCENTAGE,
#         device_class=None,
#         suggested_display_precision=0,
#     ),
# ]

SWITCH_ENTITIES = [
    ExtSwitchEntityDescription(
        tag=Tag.BATTERYDISCHARGECONTROL,
        key=Tag.BATTERYDISCHARGECONTROL.json_key,
        icon="mdi:battery-off-outline",
        entity_category=EntityCategory.CONFIG,
        device_class=None
    )
]
SWITCH_ENTITIES_PER_LOADPOINT = [
    ExtSwitchEntityDescriptionStub(
        tag=Tag.BATTERYBOOST,
        icon="mdi:battery-plus",
        icon_off="mdi:battery-plus-outline",
        device_class=None,
        entity_registry_enabled_default=True
    ),
]
