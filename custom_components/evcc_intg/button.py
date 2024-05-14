import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, BUTTONS, ExtButtonEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("BUTTON async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in BUTTONS:
        entity = EvccButton(coordinator, description)
        entities.append(entity)
    add_entity_cb(entities)


class EvccButton(EvccBaseEntity, ButtonEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtButtonEntityDescription):
        super().__init__(coordinator=coordinator, description=description)

    async def async_press(self, **kwargs):
        try:
            await self.coordinator.async_write_key(self.data_key, self.entity_description.payload, self)
        except ValueError:
            return "unavailable"