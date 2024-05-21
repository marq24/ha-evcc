import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.evcc_intg.pyevcc_ha.keys import Tag
from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, NUMBER_SENSORS, ExtNumberEntityDescription, NUMBER_SENSORS_PER_LOADPOINT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("NUMBER async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in NUMBER_SENSORS:
        entity = EvccNumber(coordinator, description)
        entities.append(entity)

    multi_loadpoint_config = len(coordinator._loadpoint) > 1
    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]

        for a_stub in NUMBER_SENSORS_PER_LOADPOINT:
            description = ExtNumberEntityDescription(
                tag = a_stub.tag,
                idx = lp_api_index,
                key = f"{a_stub.tag.key}_{lp_api_index}_{lp_id_addon}",
                translation_key = a_stub.tag.key,
                name_addon = lp_name_addon if multi_loadpoint_config else None,
                icon = a_stub.icon,
                device_class = a_stub.device_class,
                unit_of_measurement = a_stub.unit_of_measurement,
                entity_category = a_stub.entity_category,
                entity_registry_enabled_default = a_stub.entity_registry_enabled_default,

                # the entity type specific values...
                max_value = a_stub.max_value,
                min_value = a_stub.min_value,
                mode = a_stub.mode,
                native_max_value = a_stub.native_max_value,
                native_min_value = a_stub.native_min_value,
                native_step = a_stub.native_step,
                native_unit_of_measurement = a_stub.native_unit_of_measurement,
                step = a_stub.step,
            )

            if a_stub.tag == Tag.SMARTCOSTLIMIT and coordinator._cost_type == "co2":
                description.translation_key = f"{a_stub.tag.key}_co2"
                description.icon = "mdi:molecule-co2"
                description.native_max_value=500
                description.native_min_value=0
                description.native_step=5
                description.native_unit_of_measurement="g/kWh"

            entity = EvccNumber(coordinator, description)
            entities.append(entity)

    add_entity_cb(entities)


class EvccNumber(EvccBaseEntity, NumberEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtNumberEntityDescription):
        super().__init__(coordinator=coordinator, description=description)

    @property
    def native_value(self):
        try:
            value = self.coordinator.read_tag(self.tag, self.idx)
            if value is None or value == "":
                return "unknown"
            else:
                if self.tag == Tag.SMARTCOSTLIMIT:
                    value = round(float(value), 2)
                else:
                    value = int(value)

            # thanks for nothing evcc - SOC-Limit can be 0, even if the effectiveLimit is 100 - I assume you want
            # to tell that the limit is not set...
            if self.tag == Tag.LIMITSOC and value == 0:
                value = 100

        except KeyError:
            return "unknown"

        except TypeError:
            return None

        return value

    async def async_set_native_value(self, value) -> None:
        try:
            if self.tag == Tag.SMARTCOSTLIMIT:
                await self.coordinator.async_write_tag(self.tag, round(float(value), 2), self.idx, self)
            else:
                await self.coordinator.async_write_tag(self.tag, int(value), self.idx, self)

        except ValueError:
            return "unavailable"
