import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, BUTTONS, BUTTONS_PER_LOADPOINT, ExtButtonEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("BUTTON async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in BUTTONS:
        entity = EvccButton(coordinator, description)
        entities.append(entity)

    multi_loadpoint_config = len(coordinator._loadpoint) > 1
    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]
        lp_has_phase_auto_option = load_point_config["has_phase_auto_option"]

        for a_stub in BUTTONS_PER_LOADPOINT:
            description = ExtButtonEntityDescription(
                tag=a_stub.tag,
                idx=lp_api_index,
                key=f"{lp_id_addon}_{a_stub.tag.key}",
                translation_key=a_stub.tag.key,
                name_addon=lp_name_addon if multi_loadpoint_config else None,
                icon=a_stub.icon,
                device_class=a_stub.device_class,
                unit_of_measurement=a_stub.unit_of_measurement,
                entity_category=a_stub.entity_category,
                entity_registry_enabled_default=a_stub.entity_registry_enabled_default,

                # the entity type specific values...
                payload=a_stub.payload
            )

            entity = EvccButton(coordinator, description)
            entities.append(entity)

    add_entity_cb(entities)


class EvccButton(EvccBaseEntity, ButtonEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtButtonEntityDescription):
        super().__init__(coordinator=coordinator, description=description)

    async def async_press(self, **kwargs):
        try:
            await self.coordinator.async_press_tag(self.tag, self.entity_description.payload, self.idx, self)
        except ValueError:
            return "unavailable"