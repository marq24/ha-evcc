import logging

from custom_components.evcc_intg.pyevcc_ha.keys import Tag
from homeassistant.components.number import NumberEntity
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, NUMBER_SENSORS, ExtNumberEntityDescription, NUMBER_SENSORS_PER_LOADPOINT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("NUMBER async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in NUMBER_SENSORS:
        # for SEK, NOK, DKK we need to patch the maxvalue (1€ ~ 10 Krone)
        if description.tag == Tag.BATTERYGRIDCHARGELIMIT:
            if coordinator._currency != "€":
                new_val = description.native_max_value * 10
                description.native_max_value=new_val

        entity = EvccNumber(coordinator, description)
        entities.append(entity)

    multi_loadpoint_config = len(coordinator._loadpoint) > 1
    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]
        lp_has_phase_auto_option = load_point_config["has_phase_auto_option"]
        lp_is_heating = load_point_config["is_heating"]

        for a_stub in NUMBER_SENSORS_PER_LOADPOINT:
            force_celsius = lp_is_heating  and a_stub.tag == Tag.LIMITSOC

            description = ExtNumberEntityDescription(
                tag=a_stub.tag,
                idx=lp_api_index,
                key=f"{lp_id_addon}_{a_stub.tag.key}",
                translation_key=a_stub.tag.key,
                name_addon=lp_name_addon if multi_loadpoint_config else None,
                icon=a_stub.icon,
                device_class=SensorDeviceClass.TEMPERATURE if force_celsius else a_stub.device_class,
                unit_of_measurement=UnitOfTemperature.CELSIUS if force_celsius else a_stub.unit_of_measurement,
                entity_category=a_stub.entity_category,
                entity_registry_enabled_default=a_stub.entity_registry_enabled_default,

                # the entity type specific values...
                max_value=a_stub.max_value,
                min_value=a_stub.min_value,
                mode=a_stub.mode,
                native_max_value=a_stub.native_max_value,
                native_min_value=a_stub.native_min_value,
                native_step=a_stub.native_step,
                native_unit_of_measurement=UnitOfTemperature.CELSIUS if force_celsius else a_stub.native_unit_of_measurement,
                step=a_stub.step,
            )

            if a_stub.tag == Tag.SMARTCOSTLIMIT:
                if coordinator._cost_type == "co2":
                    description.translation_key = f"{a_stub.tag.key}_co2"
                    description.icon = "mdi:molecule-co2"
                    description.native_max_value=500
                    description.native_min_value=0
                    description.native_step=5
                    description.native_unit_of_measurement="g/kWh"

                # for SEK, NOK, DKK we need to patch the maxvalue (1€ ~ 10 Krone)
                elif coordinator._currency != "€":
                    new_val = a_stub.native_max_value * 10
                    description.native_max_value=new_val

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
                if self.tag == Tag.SMARTCOSTLIMIT or self.tag == Tag.BATTERYGRIDCHARGELIMIT:
                    value = round(float(value), 3)
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
            if self.tag == Tag.SMARTCOSTLIMIT or self.tag == Tag.BATTERYGRIDCHARGELIMIT:
                await self.coordinator.async_write_tag(self.tag, round(float(value), 3), self.idx, self)
            else:
                await self.coordinator.async_write_tag(self.tag, int(value), self.idx, self)

        except ValueError:
            return "unavailable"
