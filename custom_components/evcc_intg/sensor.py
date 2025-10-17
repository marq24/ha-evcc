import logging
from dataclasses import replace
from datetime import datetime, timezone
from numbers import Number

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.evcc_intg.pyevcc_ha.keys import Tag, EP_TYPE, FORECAST_CONTENT
from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import (
    DOMAIN,
    SENSOR_SENSORS,
    SENSOR_SENSORS_GRID_AS_PREFIX,
    SENSOR_SENSORS_GRID_AS_OBJECT,
    SENSOR_SENSORS_PER_LOADPOINT,
    SENSOR_SENSORS_PER_VEHICLE,
    ExtSensorEntityDescription
)
from .pyevcc_ha import SESSIONS_KEY_TOTAL

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

    multi_loadpoint_config = len(coordinator._loadpoint) > 1 #or len(coordinator._vehicle) > 1

    # loadpoint sensors...
    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]
        lp_has_phase_auto_option = load_point_config["has_phase_auto_option"]
        lp_is_heating = load_point_config["is_heating"]
        lp_is_integrated = load_point_config["is_integrated"]

        for a_stub in SENSOR_SENSORS_PER_LOADPOINT:
            if not lp_is_integrated or a_stub.integrated_supported:
                # well - a hack to show any heating related loadpoints with temperature units...
                # note: this will not change the label (that still show 'SOC')
                force_celsius = lp_is_heating  and (
                                 a_stub.tag == Tag.EFFECTIVEPLANSOC or
                                 a_stub.tag == Tag.EFFECTIVELIMITSOC or
                                 a_stub.tag == Tag.VEHICLESOC or
                                 a_stub.tag == Tag.VEHICLEMINSOC or
                                 a_stub.tag == Tag.VEHICLELIMITSOC or
                                 a_stub.tag == Tag.VEHICLEPLANSSOC)

                description = ExtSensorEntityDescription(
                    tag=a_stub.tag,
                    idx=lp_api_index,
                    key=f"{lp_id_addon}_{a_stub.tag.key}" if a_stub.array_idx is None else f"{lp_id_addon}_{a_stub.tag.key}_{a_stub.array_idx}",
                    translation_key=a_stub.tag.key if a_stub.array_idx is None else f"{a_stub.tag.key}_{a_stub.array_idx}",
                    name_addon=lp_name_addon if multi_loadpoint_config else None,
                    icon=a_stub.icon,
                    device_class=SensorDeviceClass.TEMPERATURE if force_celsius else a_stub.device_class,
                    unit_of_measurement=UnitOfTemperature.CELSIUS if force_celsius else a_stub.unit_of_measurement,
                    entity_category=a_stub.entity_category,
                    entity_registry_enabled_default=a_stub.entity_registry_enabled_default,

                    # the entity type specific values...
                    state_class=a_stub.state_class,
                    native_unit_of_measurement=UnitOfTemperature.CELSIUS if force_celsius else a_stub.native_unit_of_measurement,
                    suggested_display_precision=a_stub.suggested_display_precision,
                    array_idx=a_stub.array_idx,
                    tuple_idx=a_stub.tuple_idx,
                    factor=a_stub.factor,
                    lookup=a_stub.lookup,
                    ignore_zero=a_stub.ignore_zero
                )

                # if it's a lookup value, we just patch the translation key...
                if a_stub.lookup is not None:
                    description = replace(
                        description,
                        key = f"{description.key}_value",
                        translation_key = f"{description.translation_key}_value"
                    )

                # for charging session sensor we must patch some additional stuff...
                if a_stub.tag.type == EP_TYPE.SESSIONS:
                    if a_stub.tag.entity_key is not None:
                        description = replace(
                            description,
                            key = f"cstotal_{description.key}",
                            translation_key = a_stub.tag.entity_key,
                            name_addon = lp_name_addon if multi_loadpoint_config else None,
                        )

                entity = EvccSensor(coordinator, description)
                entities.append(entity)

    # vehicle sensors...
    for a_vehicle_key in coordinator._vehicle:
        a_vehicle_obj = coordinator._vehicle[a_vehicle_key]
        veh_id_addon = a_vehicle_obj["id"]
        veh_name_addon = a_vehicle_obj["name"]

        for a_stub in SENSOR_SENSORS_PER_VEHICLE:
            description = ExtSensorEntityDescription(
                tag=a_stub.tag,
                key=f"{veh_id_addon}_{a_stub.tag.key}" if a_stub.array_idx is None else f"{veh_id_addon}_{a_stub.tag.key}_{a_stub.array_idx}",
                translation_key=a_stub.tag.key if a_stub.array_idx is None else f"{a_stub.tag.key}_{a_stub.array_idx}",
                name_addon=veh_name_addon if multi_loadpoint_config else None,
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
                description = replace(
                    description,
                    key = f"{description.key}_value",
                    translation_key = f"{description.translation_key}_value"
                )

            # for charging session sensor we must patch some additional stuff...
            if a_stub.tag.type == EP_TYPE.SESSIONS:
                if a_stub.tag.entity_key is not None:
                    description = replace(
                        description,
                        key = f"cstotal_{description.key}",
                        translation_key = a_stub.tag.entity_key,
                        name_addon = veh_name_addon
                    )

            entity = EvccSensor(coordinator, description)
            entities.append(entity)

    add_entity_cb(entities)


class EvccSensor(EvccBaseEntity, SensorEntity, RestoreEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtSensorEntityDescription):
        super().__init__(coordinator=coordinator, description=description)
        self._previous_float_value: float | None = None
        if self.tag.type == EP_TYPE.TARIFF or self.tag == Tag.FORECAST_GRID or self.tag == Tag.FORECAST_SOLAR:
            self._last_calculated_key = None
            self._last_calculated_value = None

    @property
    def extra_state_attributes(self):
        """Return sensor attributes"""
        if self.tag.type == EP_TYPE.SESSIONS:
            if self.tag.subtype is None:
                return self.coordinator.read_tag_sessions(self.tag)

        elif self.tag.type == EP_TYPE.TARIFF:
            a_dict = self.coordinator.read_tag_tariff(self.tag)
            if a_dict is not None and "rates" in a_dict:
                a_array = a_dict["rates"]
                if a_array is not None:
                    a_array_without_end_values = [
                        {
                            "start_utc": int(datetime.fromisoformat(entry["start"]).timestamp()),
                            "value": round(entry["value"], 4) if not float(entry["value"]).is_integer() else entry["value"],
                        }
                        for entry in a_array
                    ]
                    return {"rates": a_array_without_end_values}
                else:
                    return a_dict
            else:
                return a_dict

        elif self.tag == Tag.FORECAST_GRID or self.tag == Tag.FORECAST_SOLAR:
            data = self.coordinator.read_tag(self.tag)
            if data is not None:
                if self.tag == Tag.FORECAST_GRID and FORECAST_CONTENT.GRID.value in data:
                    # thanks - with the extension to 1/4 h forcast data the content of evcc
                    # is no longer storable in HA database (exceed maximum size of 16384 bytes)
                    # so as workaround we throw away all 'end' values...
                    a_array = data[FORECAST_CONTENT.GRID.value]
                    if a_array is not None:
                        a_array_without_end_values = [
                            {
                                "start_utc": int(datetime.fromisoformat(entry["start"]).timestamp()),
                                "value": round(entry["value"], 4) if not float(entry["value"]).is_integer() else entry["value"],
                            }
                            for entry in a_array
                        ]
                        return {"rates": a_array_without_end_values}
                    else:
                        return {"rates": a_array}

                elif self.tag == Tag.FORECAST_SOLAR and FORECAST_CONTENT.SOLAR.value in data:
                    # wow - these are real vales from the evcc API:
                    # "val": 102.91332846080002
                    # how fucking useless this can be? We need even more precision...
                    # let's round this to 4 digit

                    a_object = data[FORECAST_CONTENT.SOLAR.value]
                    if "timeseries" in a_object:
                        a_array = a_object["timeseries"]
                        if a_array is not None and "ts" in a_array[0]:
                            rounded_array = [
                                {
                                    "ts_utc": int(datetime.fromisoformat(entry["ts"]).timestamp()),
                                    "val": round(entry["val"], 4) if not float(entry["val"]).is_integer() else entry["val"],
                                }
                                for entry in a_array
                            ]
                            a_object["timeseries"] = rounded_array
                        else:
                            # we have already rounded the data ?!
                            pass

                    return a_object

            #if self.tag == Tag.FORCAST_SOLAR and "timeseries" in data:
            #    data = data["timeseries"]
            #_LOGGER.error(f"ATTR: {self.tag} - {data}")
            #return data
        return None

    def get_current_value_from_timeseries(self, data_list):
        if data_list is not None:
            current_time = datetime.now(timezone.utc)
            a_key = f"{current_time.hour}_{int(current_time.minute/15) if current_time.minute > 0 else 0}"
            if a_key != self._last_calculated_key:
                self._last_calculated_key = a_key
                for a_entry in data_list:
                    if "start" in a_entry and "end" in a_entry:
                        start_dt = datetime.fromisoformat(a_entry["start"]).astimezone(timezone.utc)
                        end_dt = datetime.fromisoformat(a_entry["end"]).astimezone(timezone.utc)
                        if start_dt < current_time < end_dt:
                            if "value" in a_entry:
                                self._last_calculated_value = a_entry["value"]
                                break
                            elif "price" in a_entry:
                                self._last_calculated_value = a_entry["price"]
                                break

                    elif "ts" in a_entry or "ts_utc" in a_entry:
                        if "ts_utc" in a_entry:
                            timestamp_dt = datetime.fromtimestamp(a_entry["ts_utc"], tz=timezone.utc)
                        else:
                            timestamp_dt = datetime.fromisoformat(a_entry["ts"]).astimezone(timezone.utc)

                        if (timestamp_dt.day == current_time.day and
                            timestamp_dt.hour == current_time.hour and
                            int(timestamp_dt.minute / 15) == int(current_time.minute / 15)
                        ):
                            if "val" in a_entry:
                                self._last_calculated_value = a_entry["val"]
                                break
                            elif "value" in a_entry:
                                self._last_calculated_value = a_entry["value"]
                                break
                            elif "price" in a_entry:
                                self._last_calculated_value = a_entry["price"]
            return self._last_calculated_value
        return None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.tag.type == EP_TYPE.SESSIONS:
            attr_data = self.coordinator.read_tag_sessions(self.tag, self._attr_name_addon)
            if attr_data is not None:
                if isinstance(attr_data, (dict, list)):
                    if SESSIONS_KEY_TOTAL in attr_data:
                        return attr_data[SESSIONS_KEY_TOTAL]

                    return len(attr_data)

                if isinstance(attr_data, (Number, str)):
                    return attr_data

            return None

        if self.tag.type == EP_TYPE.TARIFF:
            attr_data = self.coordinator.read_tag_tariff(self.tag)
            if attr_data is not None and "rates" in attr_data:
                data_list = attr_data["rates"]
                if data_list is not None:
                    return self.get_current_value_from_timeseries(data_list)
                else:
                    return None
            else:
                _LOGGER.debug(f"no tariff data found for {self.tag}")
                return None
        try:
            value = self.coordinator.read_tag(self.tag, self.idx)
            if hasattr(self.entity_description, "tuple_idx") and self.entity_description.tuple_idx is not None and len(self.entity_description.tuple_idx) > 1:
                array_idx1 = self.entity_description.tuple_idx[0]
                array_idx2 = self.entity_description.tuple_idx[1]
                try:
                    value = value[array_idx1][array_idx2]
                except (IndexError, KeyError):
                    _LOGGER.debug(f"index {array_idx1} or {array_idx2} not found in {value}")
                    value = None

            elif hasattr(self.entity_description, "array_idx") and self.entity_description.array_idx is not None:
                array_idx = self.entity_description.array_idx
                try:
                    value = value[array_idx]
                except (IndexError, KeyError):
                    _LOGGER.debug(f"index {array_idx} not found in {value}")
                    value = None

            if isinstance(value, (dict, list)):
                if self.tag == Tag.FORECAST_GRID:
                    value = self.get_current_value_from_timeseries(value)
                elif self.tag == Tag.FORECAST_SOLAR:
                    if "timeseries" in value:
                        value = self.get_current_value_from_timeseries(value["timeseries"])
                    elif "today" in value and "energy" in value["today"]:
                        value = value["today"]["energy"]
                    else:
                        value = None
                else:
                    # if the value is a list (or dict), but could not be extracted (cause of none matching indices) we need
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

        except (IndexError, ValueError, TypeError, KeyError) as err:
            _LOGGER.debug(f"tag: {self.tag} (idx: '{self.idx}') (value: '{value}') caused {err}")
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