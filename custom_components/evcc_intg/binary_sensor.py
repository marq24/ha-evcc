import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, BINARY_SENSORS, BINARY_SENSORS_PER_LOADPOINT, ExtBinarySensorEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("BINARY_SENSOR async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in BINARY_SENSORS:
        entity = EvccBinarySensor(coordinator, description)
        entities.append(entity)

    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]
        lp_has_phase_auto_option = load_point_config["has_phase_auto_option"]

        for a_stub in BINARY_SENSORS_PER_LOADPOINT:
            description = ExtBinarySensorEntityDescription(
                tag=a_stub.tag,
                idx=lp_api_index,
                key=f"{a_stub.tag.key}_{lp_api_index}_{lp_id_addon}",
                translation_key=a_stub.tag.key,
                name_addon=lp_name_addon,
                icon=a_stub.icon,
                device_class=a_stub.device_class,
                unit_of_measurement=a_stub.unit_of_measurement,
                entity_category=a_stub.entity_category,
                entity_registry_enabled_default=a_stub.entity_registry_enabled_default,

                # the entity type specific values...
                icon_off=a_stub.icon_off
            )

            entity = EvccBinarySensor(coordinator, description)
            entities.append(entity)

    add_entity_cb(entities)


class EvccBinarySensor(EvccBaseEntity, BinarySensorEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtBinarySensorEntityDescription):
        super().__init__(coordinator=coordinator, description=description)
        self._attr_icon_off = self.entity_description.icon_off

    @property
    def is_on(self) -> bool | None:
        try:
            value = self.coordinator.read_tag(self.tag, self.idx)

        except IndexError:
            if self.entity_description.idx is not None:
                _LOGGER.debug(f"lc-key: {self.tag.key.lower()} value: {value} idx: {self.idx} -> {self.coordinator.data[self.tag.key]}")
            else:
                _LOGGER.debug(f"lc-key: {self.tag.key.lower()} caused IndexError")
            value = None
        except KeyError:
            _LOGGER.warning(f"is_on caused KeyError for: {self.tag.key}")
            value = None
        except TypeError:
            return None

        if not isinstance(value, bool):
            if isinstance(value, str):
                # parse anything else then 'on' to False!
                if value.lower() == 'on':
                    value = True
                else:
                    value = False
            else:
                value = False

        return value

    @property
    def icon(self):
        """Return the icon of the sensor."""
        if self._attr_icon_off is not None and self.state == STATE_OFF:
            return self._attr_icon_off
        else:
            return super().icon
