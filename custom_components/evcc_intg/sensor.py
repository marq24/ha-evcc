import logging

from custom_components.evcc_intg.pyevcc_ha.keys import Tag
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, SENSOR_SENSORS, SENSOR_SENSORS_GRID_AS_PREFIX, SENSOR_SENSORS_GRID_AS_OBJECT, \
    SENSOR_SENSORS_PER_LOADPOINT, ExtSensorEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("SENSOR async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in SENSOR_SENSORS:
        entity = EvccSensor(coordinator, description)
        entities.append(entity)

    # we need to check if the grid data (power & currents) is available as separate object...
    # or if it's still part of the main/site object (as gridPower, gridCurrents)
    if coordinator.grid_data_as_object:
        _LOGGER.debug("evcc 'grid' data is available as separate object")
        for description in SENSOR_SENSORS_GRID_AS_OBJECT:
            entity = EvccSensor(coordinator, description)
            entities.append(entity)
    else:
        _LOGGER.debug("evcc 'grid' as prefix")
        for description in SENSOR_SENSORS_GRID_AS_PREFIX:
            entity = EvccSensor(coordinator, description)
            entities.append(entity)

    multi_loadpoint_config = len(coordinator._loadpoint) > 1
    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]
        lp_has_phase_auto_option = load_point_config["has_phase_auto_option"]

        for a_stub in SENSOR_SENSORS_PER_LOADPOINT:
            description = ExtSensorEntityDescription(
                tag=a_stub.tag,
                idx=lp_api_index,
                key=f"{lp_id_addon}_{a_stub.tag.key}" if a_stub.array_idx is None else f"{lp_id_addon}_{a_stub.tag.key}_{a_stub.array_idx}",
                translation_key=a_stub.tag.key if a_stub.array_idx is None else f"{a_stub.tag.key}_{a_stub.array_idx}",
                name_addon=lp_name_addon if multi_loadpoint_config else None,
                icon=a_stub.icon,
                device_class=a_stub.device_class,
                unit_of_measurement=a_stub.unit_of_measurement,
                entity_category=a_stub.entity_category,
                entity_registry_enabled_default=a_stub.entity_registry_enabled_default,

                # the entity type specific values...
                state_class=a_stub.state_class,
                native_unit_of_measurement=a_stub.native_unit_of_measurement,
                suggested_display_precision=a_stub.suggested_display_precision,
                array_idx=a_stub.array_idx,
                tuple_idx=a_stub.tuple_idx,
                factor=a_stub.factor,
                lookup=a_stub.lookup,
                ignore_zero=a_stub.ignore_zero
            )

            # if it's a lookup value, we just patch the translation key...
            if a_stub.lookup is not None:
                description.key = f"{description.key}_value"
                description.translation_key = f"{description.translation_key}_value"


            entity = EvccSensor(coordinator, description)
            entities.append(entity)

    add_entity_cb(entities)


class EvccSensor(EvccBaseEntity, SensorEntity, RestoreEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtSensorEntityDescription):
        super().__init__(coordinator=coordinator, description=description)
        self._previous_float_value: float | None = None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            value = self.coordinator.read_tag(self.tag, self.idx)
            if isinstance(value, list):
                if self.entity_description.tuple_idx is not None and len(self.entity_description.tuple_idx) > 1:
                    array_idx1 = self.entity_description.tuple_idx[0]
                    array_idx2 = self.entity_description.tuple_idx[1]
                    if len(value) > array_idx1 or array_idx1 in value:
                        value = value[array_idx1]
                        if isinstance(value, list) and len(value) > array_idx2 or array_idx2 in value:
                            value = value[array_idx2]

                elif self.entity_description.array_idx is not None:
                    array_idx = self.entity_description.array_idx
                    if len(value) > array_idx or array_idx in value:
                        value = value[array_idx]

                if isinstance(value, list):
                    # if the value is a list, but could not be extracted (cause of none matching indices) we need
                    # to purge the value to None!
                    value = None

            if value is None or len(str(value)) == 0:
                value = None
            else:
                if self.entity_description.lookup is not None:
                    if self.tag.key.lower() in self.coordinator.lang_map:
                        value = self.coordinator.lang_map[self.tag.key.lower()][value]
                    else:
                        _LOGGER.warning(f"{self.tag.key} not found in translations")
                elif isinstance(value, bool):
                    if value is True:
                        value = "on"
                    elif value is False:
                        value = "off"
                else:
                    # self.entity_description.lookup values are always 'strings' - so there we should not
                    # have an additional 'factor'
                    if self.entity_description.factor is not None:
                        value = float(value)/self.entity_description.factor

        except (IndexError, ValueError, TypeError):
            value = None

        # make sure that we do not return unknown or smaller values
        # [see https://github.com/marq24/ha-evcc/discussions/7]
        if self.tag == Tag.CHARGETOTALIMPORT:
            if value is None or value == "unknown":
                if self._previous_float_value is not None:
                    return self._previous_float_value
            else:
                a_float_value = float(value)
                if self._previous_float_value is not None and a_float_value < self._previous_float_value:
                    _LOGGER.debug(f"prev>new for key {self._attr_translation_key} [prev: '{self._previous_float_value}' new: '{a_float_value}']")
                    return self._previous_float_value
                else:
                    self._previous_float_value = a_float_value

        # make sure that we only return values > 0
        if self.entity_description.ignore_zero:
            isZeroVal = value is None or value == "unknown" or value <= 0.1

            if isZeroVal and self._previous_float_value is not None and self._previous_float_value > 0:
                value = self._previous_float_value
            elif value > 0:
                self._previous_float_value = value

        # final return statement...
        return value