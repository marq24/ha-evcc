import logging
from typing import Literal

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, SWITCH_SENSORS, ExtSwitchEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("SWITCH async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in SWITCH_SENSORS:
        entity = EvccSwitch(coordinator, description)
        entities.append(entity)
    add_entity_cb(entities)


class EvccSwitch(EvccBaseEntity, SwitchEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtSwitchEntityDescription):
        super().__init__(coordinator=coordinator, description=description)
        self._attr_icon_off = self.entity_description.icon_off

    async def async_turn_on(self, **kwargs):
       """Turn on the switch."""
       try:
           if self.entity_description.is_zero_or_one:
               await self.coordinator.async_write_key(self.data_key, 1, self)
           else:
               await self.coordinator.async_write_key(self.data_key, True, self)
           return self.coordinator.data[self.data_key]
       except ValueError:
           return "unavailable"

    async def async_turn_off(self, **kwargs):
       """Turn off the switch."""
       try:
           if self.entity_description.is_zero_or_one:
               await self.coordinator.async_write_key(self.data_key, 0, self)
           else:
               await self.coordinator.async_write_key(self.data_key, False, self)
           return self.coordinator.data[self.data_key]
       except ValueError:
           return "unavailable"

    @property
    def is_on(self) -> bool | None:
        try:
            value = None
            if self.coordinator.data is not None:
                if self.data_key in self.coordinator.data:
                    value = self.coordinator.data[self.data_key]
                else:
                    if len(self.coordinator.data) > 0:
                        _LOGGER.info(f"is_on: for {self.data_key} not found in data: {len(self.coordinator.data)}")
                if value is None or value == "":
                    value = None

        except KeyError:
            _LOGGER.warning(f"is_on caused KeyError for: {self.data_key}")
            value = None
        except TypeError:
            return None

        if not isinstance(value, bool):
            if isinstance(value, int):
                if value > 0:
                    value = True
                else:
                    value = False
            elif isinstance(value, str):
                # parse anything else then 'on' to False!
                if value.lower() == 'on':
                    value = True
                else:
                    value = False
            else:
                value = False

        return value

    @property
    def state(self) -> Literal["on", "off"] | None:
        """Return the state."""
        if (is_on := self.is_on) is None:
            return None
        return STATE_ON if is_on else STATE_OFF

    @property
    def icon(self):
        """Return the icon of the sensor."""
        if self._attr_icon_off is not None and self.state == STATE_OFF:
            return self._attr_icon_off
        else:
            return super().icon
