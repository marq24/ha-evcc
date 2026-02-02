import logging
from dataclasses import replace
from datetime import datetime, timezone
from numbers import Number

from custom_components.evcc_intg.pyevcc_ha.keys import Tag, EP_TYPE, FORECAST_CONTENT
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import (
    DOMAIN,
    SENSOR_ENTITIES,
    SENSOR_ENTITIES_GRID_AS_PREFIX,
    SENSOR_ENTITIES_GRID_AS_OBJECT,
    SENSOR_ENTITIES_BATTERY_AS_PREFIX,
    SENSOR_ENTITIES_BATTERY_AS_OBJECT,
    SENSOR_ENTITIES_PER_LOADPOINT,
    SENSOR_ENTITIES_PER_VEHICLE,
    SENSOR_ENTITIES_PER_CIRCUIT,
    TAG_TO_CONTENT_KEY,
    ExtSensorEntityDescription
)
from .pyevcc_ha import SESSIONS_KEY_TOTAL
from .pyevcc_ha.const import (
    JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGED_TOTAL,
    JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGING_POWER,
    JSONKEY_EVOPT_RES_BATTERIES_AINDEX_DISCHARGING_POWER,
    JSONKEY_EVOPT_DETAILS_BATTERYDETAILS,
    JSONKEY_EVOPT_DETAILS_TIMESTAMP
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("SENSOR async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    the_sensors_list = SENSOR_ENTITIES

    # we need to check if the grid data (power & currents) is available as separate object...
    # or if it's still part of the main/site object (as gridPower, gridCurrents)
    if coordinator.grid_data_as_object:
        _LOGGER.debug("evcc 'grid' data is available in separate object")
        the_sensors_list = the_sensors_list + SENSOR_ENTITIES_GRID_AS_OBJECT
    else:
        _LOGGER.debug("evcc 'grid' as prefix")
        the_sensors_list = the_sensors_list + SENSOR_ENTITIES_GRID_AS_PREFIX

    # additionally, the battery sensors can be either with prefix (at least till
    # evcc 0.209.7), or as a separate 'battery' object
    if coordinator.battery_data_as_object:
        _LOGGER.debug("evcc 'battery' data is available in separate object")
        the_sensors_list = the_sensors_list + SENSOR_ENTITIES_BATTERY_AS_OBJECT
    else:
        _LOGGER.debug("evcc 'battery' as prefix")
        the_sensors_list = the_sensors_list + SENSOR_ENTITIES_BATTERY_AS_PREFIX

    # finally creating all the Sensors, based on the descriptions
    for description in the_sensors_list:
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

        for a_stub in SENSOR_ENTITIES_PER_LOADPOINT:
            if not lp_is_integrated or a_stub.integrated_supported:
                # well - a hack to show any heating related loadpoints with temperature units...
                # note: this will not change the label (that still show 'SOC')
                force_celsius = lp_is_heating  and (
                        a_stub.tag == Tag.EFFECTIVEPLANSOC or
                        a_stub.tag == Tag.EFFECTIVELIMITSOC or
                        a_stub.tag == Tag.LP_VEHICLESOC or
                        a_stub.tag == Tag.LP_VEHICLELIMITSOC or
                        a_stub.tag == Tag.VEHICLEMINSOC or
                        a_stub.tag == Tag.VEHICLELIMITSOC or
                        a_stub.tag == Tag.VEHICLEPLANSOC)

                # only when the json_idx has a length of 1 we must patch our key & translation_key
                patch_keys = a_stub.json_idx is not None and len(a_stub.json_idx) == 1

                description = ExtSensorEntityDescription(
                    tag=a_stub.tag,
                    lp_idx=lp_api_index,
                    key=f"{lp_id_addon}_{a_stub.tag.json_key}" if not patch_keys else f"{lp_id_addon}_{a_stub.tag.json_key}_{a_stub.json_idx[0]}",
                    translation_key=a_stub.tag.json_key if not patch_keys else f"{a_stub.tag.json_key}_{a_stub.json_idx[0]}",
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
                    json_idx=a_stub.json_idx,
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

        for a_stub in SENSOR_ENTITIES_PER_VEHICLE:
            # only when the json_idx has a length of 1 we must patch our key & translation_key
            patch_keys = a_stub.json_idx is not None and len(a_stub.json_idx) == 1

            description = ExtSensorEntityDescription(
                tag=a_stub.tag,
                key=f"{veh_id_addon}_{a_stub.tag.json_key}" if not patch_keys else f"{veh_id_addon}_{a_stub.tag.json_key}_{a_stub.json_idx[0]}",
                translation_key=a_stub.tag.json_key if not patch_keys else f"{a_stub.tag.json_key}_{a_stub.json_idx[0]}",
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
                json_idx=a_stub.json_idx,
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

    # the additional circuit entities...
    if coordinator._circuit is not None and len(coordinator._circuit) > 0:
        for a_circuit_key in coordinator._circuit:
            # a_circuit_config = coordinator._circuit[a_circuit_key]
            for a_stub in SENSOR_ENTITIES_PER_CIRCUIT:
                if a_stub.integrated_supported:
                    the_key = a_stub.tag.entity_key if a_stub.tag.entity_key is not None else a_stub.tag.json_key
                    description = ExtSensorEntityDescription(
                        tag=a_stub.tag,
                        #key=a_stub.tag.entity_key if a_stub.tag.entity_key is not None else a_stub.tag.json_key,
                        key=f"{a_circuit_key}_{the_key}",
                        translation_key=the_key,
                        lp_idx=a_circuit_key,
                        name_addon=f"'{a_circuit_key.upper()}'",
                        icon=a_stub.icon,
                        entity_category=a_stub.entity_category,
                        entity_registry_enabled_default=a_stub.entity_registry_enabled_default,

                        # the entity type specific values...
                        state_class=a_stub.state_class,
                        native_unit_of_measurement=a_stub.native_unit_of_measurement,
                        suggested_display_precision=a_stub.suggested_display_precision,
                        json_idx=a_stub.json_idx,
                        factor=a_stub.factor,
                        lookup=a_stub.lookup,
                        ignore_zero=a_stub.ignore_zero
                    )

                    entity = EvccSensor(coordinator, description)
                    entities.append(entity)

    add_entity_cb(entities)

def compress_data(data):
    return compress_general(data, "start", "value")

def compress_timeseries(data):
    return compress_general(data, "ts", "val")

def compress_general(data, time_key:str, value_key:str):
    # Ensure the data is not empty
    if not data:
        return {"start_utc": None,
                "deltas_in_minutes": [],
                "values": []}

    # Convert the timestamps to UTC and prepare the output
    start_timestamp_utc = datetime.fromisoformat(data[0][time_key]).astimezone(timezone.utc).isoformat()
    values = [round(entry[value_key], 4) if not float(entry[value_key]).is_integer() else entry[value_key] for entry in data]
    deltas = []
    for i in range(1, len(data)):
        # Calculate time difference in minutes
        ts_current = datetime.fromisoformat(data[i][time_key]).astimezone(timezone.utc)
        ts_previous = datetime.fromisoformat(data[i - 1][time_key]).astimezone(timezone.utc)
        delta = int((ts_current - ts_previous).total_seconds() // 60.0)
        deltas.append(delta)

    # {%set json_data=state_attr('sensor.evcc_forecast_grid', 'rates')%}
    # {% set total_minutes_since_start = (( now() - strptime(json_data['start_utc'], '%Y-%m-%dT%H:%M:%S%z')).total_seconds() // 60)|int %}
    # {% set tmp = namespace(total=0, index=0) %}
    # {% for delta in json_data['deltas_in_minutes'] %}
    #     {% if tmp.total < total_minutes_since_start %}
    #         {% set tmp.total = tmp.total + delta %}
    #         {% set tmp.index = tmp.index + 1 %}
    #     {% else %}
    #         {% break %}
    #     {% endif %}
    # {% endfor %}
    # {% set relevant_values = json_data['values'][tmp.index:] %}
    # {% set average_value = (relevant_values|sum) / relevant_values|length if relevant_values|length > 0 else 0 %}
    # {{ average_value }}

    # VALUE NOW:
    # {{json_data['values'][tmp.index]}}

    # SIMPLE AVG value
    # {%set json_data=state_attr('sensor.evcc_forecast_solar', 'timeseries')%}
    # {{json_data['values']|sum / json_data['values']|length}}

    return {"start_utc":start_timestamp_utc,
            "deltas_in_minutes": deltas,
            "values": values}


class EvccSensor(EvccBaseEntity, SensorEntity, RestoreEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtSensorEntityDescription):
        super().__init__(entity_type=Platform.SENSOR, coordinator=coordinator, description=description)
        self._previous_float_value: float | None = None
        if self.tag.type == EP_TYPE.TARIFF or self.tag in [Tag.FORECAST_GRID, Tag.FORECAST_SOLAR, Tag.FORECAST_FEEDIN, Tag.FORECAST_PLANNER]:
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
                    return {"rates": compress_data(a_array)}
                else:
                    return {"rates": a_array}
            else:
                return a_dict

        elif self.tag in [Tag.FORECAST_GRID, Tag.FORECAST_SOLAR, Tag.FORECAST_FEEDIN, Tag.FORECAST_PLANNER]:
            data = self.coordinator.read_tag(self.tag)
            if data is not None:
                if self.tag in [Tag.FORECAST_GRID, Tag.FORECAST_FEEDIN, Tag.FORECAST_PLANNER]:
                    if self.tag in TAG_TO_CONTENT_KEY:
                        content_key = TAG_TO_CONTENT_KEY[self.tag]
                        if content_key in data:
                            # evcc 1/4h forecast data exceeds HA database limit (16384 bytes).
                            # Workaround: compress by stripping 'end' values via compress_data.
                            a_array = data[content_key]
                            if a_array is not None:
                                return {"rates": compress_data(a_array)}
                            else:
                                return {"rates": a_array}

                elif self.tag == Tag.FORECAST_SOLAR and FORECAST_CONTENT.SOLAR.value in data:
                    a_object = data[FORECAST_CONTENT.SOLAR.value]
                    if "timeseries" in a_object:
                        a_copy_object = a_object.copy()
                        a_array = a_copy_object["timeseries"]
                        if a_array is not None and "ts" in a_array[0]:
                            a_copy_object["timeseries"] = compress_timeseries(a_array)
                        else:
                            a_copy_object["timeseries"] = a_array

                        return a_copy_object
                    else:
                        # return the original object
                        return a_object

        elif self.tag.type == EP_TYPE.EVOPT:
            try:
                # json_idx=[JSONKEY_EVOPT_RES_BATTERIES, 0, JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGED_TOTAL, 0],

                value = self.coordinator.read_tag(self.tag, self.lp_idx)
                if hasattr(self.entity_description, "json_idx") and self.entity_description.json_idx is not None:
                    # the Tag.EVOPT_RESULT_OBJECT is very special - we need also the name from the
                    # details...
                    a_details_obj = None
                    a_ts = None
                    if self.tag == Tag.EVOPT_RESULT_OBJECT and len(self.entity_description.json_idx) > 2:
                        if self.entity_description.json_idx[2] in [JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGED_TOTAL,
                                                                   JSONKEY_EVOPT_RES_BATTERIES_AINDEX_CHARGING_POWER,
                                                                   JSONKEY_EVOPT_RES_BATTERIES_AINDEX_DISCHARGING_POWER]:

                            name_index = int(self.entity_description.json_idx[1])
                            details_obj = self.coordinator.read_tag(Tag.EVOPT_DETAILS_OBJECT, self.lp_idx)
                            if len(details_obj[JSONKEY_EVOPT_DETAILS_BATTERYDETAILS]) > name_index:
                                a_details_obj = details_obj[JSONKEY_EVOPT_DETAILS_BATTERYDETAILS][name_index]

                            if len(details_obj[JSONKEY_EVOPT_DETAILS_TIMESTAMP]) > name_index:
                                a_ts = details_obj[JSONKEY_EVOPT_DETAILS_TIMESTAMP][name_index]

                            # *big sigh* - all is an array - but for WHATEVER reason the timestamp info
                            # is only AVAILABLE as a single entry in the list - yes, I know evopt is 'experimental'
                            # but this came out of nowhere!
                            elif len(details_obj[JSONKEY_EVOPT_DETAILS_TIMESTAMP]) == 1:
                                a_ts = details_obj[JSONKEY_EVOPT_DETAILS_TIMESTAMP][0]

                    for idx, key in enumerate(self.entity_description.json_idx[:-1]):
                        try:
                            value = value[key]
                        except (IndexError, KeyError, TypeError):
                            # we brute force our way through the dict/list and if there is an index error,
                            # we just return None (and ignoring also all other possible additional attributes)
                            value = None
                            break

                    if value is not None:
                        return_obj = {"values": value}
                        if a_details_obj is not None:
                            return_obj.update(a_details_obj)
                        if a_ts is not None:
                            return_obj[JSONKEY_EVOPT_DETAILS_TIMESTAMP] = a_ts

                        return return_obj
            except (IndexError, ValueError, TypeError, KeyError) as ex:
                _LOGGER.info(f"Error reading tag {self.tag} ({self.lp_idx}): {ex}")

        return {}

    def get_current_value_from_timeseries(self, data_list):
        if data_list is not None:
            current_time = datetime.now(timezone.utc)
            a_key = f"{current_time.hour}_{int(current_time.minute//15) if current_time.minute > 0 else 0}"
            if a_key != self._last_calculated_key:
                self._last_calculated_key = a_key
                for a_entry in data_list:
                    if "start" in a_entry and "end" in a_entry:
                        start_dt = datetime.fromisoformat(a_entry["start"]).astimezone(timezone.utc)
                        end_dt = datetime.fromisoformat(a_entry["end"]).astimezone(timezone.utc)
                        if start_dt < current_time < end_dt:
                            if "val" in a_entry:
                                self._last_calculated_value = a_entry["val"]
                                break
                            elif "value" in a_entry:
                                self._last_calculated_value = a_entry["value"]
                                break
                            elif "price" in a_entry:
                                self._last_calculated_value = a_entry["price"]
                                break

                    elif "ts" in a_entry:
                        timestamp_dt = datetime.fromisoformat(a_entry["ts"]).astimezone(timezone.utc)
                        if (timestamp_dt.day == current_time.day and
                            timestamp_dt.hour == current_time.hour and
                            int(timestamp_dt.minute // 15) == int(current_time.minute // 15)
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
            value = self.coordinator.read_tag(self.tag, self.lp_idx)
            if hasattr(self.entity_description, "json_idx") and self.entity_description.json_idx is not None:
                for idx, key in enumerate(self.entity_description.json_idx):
                    if isinstance(value, (list, dict)):
                        if isinstance(key, int) and len(value) > key:
                            value = value[key]
                        elif key in value:
                            value = value[key]
                    else:
                        try:
                            value = value[key]
                        except (IndexError, KeyError, TypeError):
                            _LOGGER.info(f"native_value(): index {idx+1} ({key}) not found in {value}")
                            value = None
                            break

            if isinstance(value, (dict, list)):
                if self.tag in [Tag.FORECAST_GRID, Tag.FORECAST_FEEDIN, Tag.FORECAST_PLANNER]:
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
                    if self.tag.json_key.lower() in self.coordinator.lang_map:
                        value = self.coordinator.lang_map[self.tag.json_key.lower()][value]
                    else:
                        _LOGGER.warning(f"{self.tag.json_key} not found in translations")
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
            _LOGGER.debug(f"tag: {self.tag} (lp_idx: '{self.lp_idx}') (value: '{value}') caused {err}")
            value = None


        # a fallback, if there is no LP_VEHICLELIMITSOC set at the loadpoint
        if self.tag == Tag.LP_VEHICLELIMITSOC and (value is None or value == 0):
            value = self.coordinator.read_tag(Tag.EFFECTIVELIMITSOC, self.lp_idx)

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