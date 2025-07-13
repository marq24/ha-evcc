import logging
from typing import Literal

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, SWITCH_SENSORS, SWITCH_SENSORS_PER_LOADPOINT, ExtSwitchEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("SWITCH async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in SWITCH_SENSORS:
        entity = EvccSwitch(coordinator, description)
        entities.append(entity)

    multi_loadpoint_config = len(coordinator._loadpoint) > 1
    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]
        lp_has_phase_auto_option = load_point_config["has_phase_auto_option"]
        lp_is_heating = load_point_config["is_heating"]
        lp_is_integrated = load_point_config["is_integrated"]

        for a_stub in SWITCH_SENSORS_PER_LOADPOINT:
            if not lp_is_integrated or a_stub.integrated_supported:
                description = ExtSwitchEntityDescription(
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
                    icon_off=a_stub.icon_off
                )

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
           # cause of a minor bug in evcc, we need to write 1 instead of True
           await self.coordinator.async_write_tag(self.tag, 1, self.idx, self)
       except ValueError:
           return "unavailable"

    async def async_turn_off(self, **kwargs):
       """Turn off the switch."""
       try:
            # cause of a minor bug in evcc, we need to write 0 instead of False
            await self.coordinator.async_write_tag(self.tag, 0, self.idx, self)
       except ValueError:
           return "unavailable"

    @property
    def is_on(self) -> bool | None:
        try:
            value = self.coordinator.read_tag(self.tag, self.idx)

        except KeyError:
            _LOGGER.info(f"is_on caused KeyError for: {self.tag.key}")
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
