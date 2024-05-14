import logging
from datetime import datetime, time

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, SENSOR_SENSORS, ExtSensorEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("SENSOR async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in SENSOR_SENSORS:
        entity = EvccSensor(coordinator, description)
        entities.append(entity)
    add_entity_cb(entities)


class EvccSensor(EvccBaseEntity, SensorEntity, RestoreEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtSensorEntityDescription):
        super().__init__(coordinator=coordinator, description=description)

    @property
    def state(self):
        """Return the state of the sensor."""
        try:
            if self.entity_description.idx is not None:
                value = self.coordinator.data[self.data_key][self.entity_description.idx]
            else:
                value = self.coordinator.data[self.data_key]

            if value is None or value == "":
                value = "unknown"
            else:
                if self.entity_description.lookup is not None:
                    if self.data_key.lower() in self.coordinator.lang_map:
                        value = self.coordinator.lang_map[self.data_key.lower()][value]
                    else:
                        _LOGGER.warning(f"{self.data_key} not found in translations")

                if self.entity_description.factor is not None and self.entity_description.factor > 0:
                    if isinstance(value, int):
                        value = int(value/self.entity_description.factor)
                    else:
                        value = value/self.entity_description.factor

                if isinstance(value, datetime):
                    return value.isoformat(sep=' ', timespec="minutes")
                elif isinstance(value, time):
                    return value.isoformat(timespec="minutes")
                elif self.entity_description.suggested_display_precision is not None:
                    value = round(float(value), self.entity_description.suggested_display_precision)

        except IndexError:
            if self.entity_description.lookup is not None:
                _LOGGER.debug(f"lc-key: {self.data_key.lower()} value: {value} -> {self.coordinator.lang_map[self.data_key.lower()]}")
            else:
                _LOGGER.debug(f"lc-key: {self.data_key.lower()} caused IndexError")
            value = "unknown"
        except KeyError:
            value = "unknown"
        except TypeError:
            return "unknown"
        if value is True:
            value = "on"
        elif value is False:
            value = "off"
        return value
