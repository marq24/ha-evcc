import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from custom_components.evcc_intg.pyevcc_ha import EvccApiBridge, TRANSLATIONS
from custom_components.evcc_intg.pyevcc_ha.const import (
    JSONKEY_LOADPOINTS,
    JSONKEY_VEHICLES,
    JSONKEY_PLANS,
    JSONKEY_PLANS_SOC,
    JSONKEY_PLANS_TIME,
    JSONKEY_STATISTICS,
    JSONKEY_STATISTICS_TOTAL,
    JSONKEY_STATISTICS_THISYEAR,
    JSONKEY_STATISTICS_365D,
    JSONKEY_STATISTICS_30D,
)
from custom_components.evcc_intg.pyevcc_ha.keys import Tag, EP_TYPE, camel_to_snake
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, Event, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as config_val  # , translation
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.typing import UNDEFINED, UndefinedType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import slugify
from .const import (
    NAME,
    DOMAIN,
    MANUFACTURER,
    PLATFORMS,
    STARTUP_MESSAGE,
    SERVICE_SET_LOADPOINT_PLAN,
    SERVICE_SET_VEHICLE_PLAN,
    CONF_INCLUDE_EVCC
)
from .service import EvccService

_LOGGER: logging.Logger = logging.getLogger(__package__)

SCAN_INTERVAL = timedelta(seconds=10)
CONFIG_SCHEMA = config_val.removed(DOMAIN, raise_if_present=False)


async def async_setup(hass: HomeAssistant, config: dict):  # pylint: disable=unused-argument
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    if DOMAIN not in hass.data:
        value = "UNKOWN"
        _LOGGER.info(STARTUP_MESSAGE)
        hass.data.setdefault(DOMAIN, {"manifest_version": value})

    coordinator = EvccDataUpdateCoordinator(hass, config_entry)
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady
    else:
        await coordinator.read_evcc_config_on_startup()

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if config_entry.state != ConfigEntryState.LOADED:
        config_entry.add_update_listener(async_reload_entry)

    # initialize our service...
    services = EvccService(hass, config_entry, coordinator)
    hass.services.async_register(DOMAIN, SERVICE_SET_LOADPOINT_PLAN, services.set_loadpoint_plan,
                                 supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SET_VEHICLE_PLAN, services.set_vehicle_plan,
                                 supports_response=SupportsResponse.OPTIONAL)

    # Do we need to patch something?!
    # if coordinator.check_for_max_of_16a:
    #     asyncio.create_task(coordinator.check_for_16a_limit(hass, config_entry.entry_id))

    # ok we are done...
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    if unload_ok:
        if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][config_entry.entry_id]
            coordinator.clear_data()
            hass.data[DOMAIN].pop(config_entry.entry_id)

        hass.services.async_remove(DOMAIN, SERVICE_SET_LOADPOINT_PLAN)
        hass.services.async_remove(DOMAIN, SERVICE_SET_VEHICLE_PLAN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload config entry."""
    if await async_unload_entry(hass, config_entry):
        await asyncio.sleep(2)
        await async_setup_entry(hass, config_entry)


class EvccDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry):
        _LOGGER.debug(f"starting evcc_intg for: {config_entry.options}\n{config_entry.data}")
        lang = hass.config.language.lower()
        self.name = config_entry.title
        self.bridge = EvccApiBridge(host=config_entry.options.get(CONF_HOST, config_entry.data.get(CONF_HOST)),
                                    web_session=async_get_clientsession(hass),
                                    lang=lang)

        global SCAN_INTERVAL
        SCAN_INTERVAL = timedelta(seconds=config_entry.options.get(CONF_SCAN_INTERVAL,
                                                                   config_entry.data.get(CONF_SCAN_INTERVAL, 5)))

        self.include_evcc_prefix = config_entry.options.get(CONF_INCLUDE_EVCC,
                                                            config_entry.data.get(CONF_INCLUDE_EVCC, False))

        # we want a some sort of unique identifier that can be selected by the user
        # during the initial configuration phase
        self._system_id = slugify(config_entry.title)

        self.lang_map = None
        if lang in TRANSLATIONS:
            self.lang_map = TRANSLATIONS[lang]
        else:
            self.lang_map = TRANSLATIONS["en"]

        # config_entry only need for providing the '_device_info_dict'...
        self._config_entry = config_entry

        # attribute creation
        self._cost_type = None
        self._currency = "€"
        self._device_info_dict = {}
        self._loadpoint = {}
        self._vehicle = {}
        self._version = None

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    # Callable[[Event], Any]
    def __call__(self, evt: Event) -> bool:
        _LOGGER.debug(f"Event arrived: {evt}")
        return True

    def clear_data(self):
        _LOGGER.debug(f"clear_data called...")
        self.bridge.clear_data()
        self.data.clear()

    async def read_evcc_config_on_startup(self):
        # we will fetch th config from evcc:
        # b) vehicles
        # a) how many loadpoints
        # c) load point configuration (like 1/3 phase options)

        initdata = await self.bridge.read_all_data()
        if Tag.VERSION.key in initdata:
            self._version = initdata[Tag.VERSION.key]
        elif Tag.AVAILABLEVERSION.key in initdata:
            self._version = initdata[Tag.AVAILABLEVERSION.key]

        self._device_info_dict = {
            "identifiers": {
                ("DOMAIN", DOMAIN),
                ("IP", self._config_entry.options.get(CONF_HOST, self._config_entry.data.get(CONF_HOST))),
            },
            "manufacturer": MANUFACTURER,
            "name": NAME,
            "sw_version": self._version
        }

        for a_veh_name in initdata[JSONKEY_VEHICLES]:
            a_veh = initdata[JSONKEY_VEHICLES][a_veh_name]
            if "capacity" in a_veh:
                self._vehicle[a_veh_name] = {
                    "name": a_veh["title"],
                    "capacity": a_veh["capacity"]
                }
            else:
                self._vehicle[a_veh_name] = {
                    "name": a_veh["title"],
                    "capacity": None
                }

        api_index = 1
        for a_loadpoint in initdata[JSONKEY_LOADPOINTS]:
            phaseSwitching = False
            if "chargerPhases1p3p" in a_loadpoint:
                phaseSwitching = a_loadpoint["chargerPhases1p3p"]
            elif "chargerPhaseSwitching" in a_loadpoint:
                phaseSwitching = a_loadpoint["chargerPhaseSwitching"]
            else:
                phaseSwitching = False

            self._loadpoint[f"{api_index}"] = {
                "name": a_loadpoint["title"],
                "id": slugify(a_loadpoint["title"]),
                "has_phase_auto_option": phaseSwitching,
                "vehicle_key": a_loadpoint["vehicleName"],
                "obj": a_loadpoint
            }
            api_index += 1

        if "smartCostType" in initdata:
            self._cost_type = initdata["smartCostType"]
        else:
            self._cost_type = "co2"

        if "currency" in initdata:
            self._currency = initdata["currency"]
            if self._currency == "EUR":
                self._currency = "€"

        _LOGGER.debug(
            f"read_evcc_config: LPs: {len(self._loadpoint)} VEHs: {len(self._vehicle)} CT: '{self._cost_type}' CUR: {self._currency}")

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        _LOGGER.debug(f"_async_update_data called")
        try:
            # if self.data is not None:
            #    _LOGGER.debug(f"number of fields before query: {len(self.data)} ")
            # result = await self.bridge.read_all()
            # _LOGGER.debug(f"number of fields after query: {len(result)}")
            # return result

            result = await self.bridge.read_all()
            if result is not None:
                _LOGGER.debug(f"number of fields after query: {len(result)}")

            # if self.data is not None:
            #     if 'prioritySoc' in self.data:
            #         _LOGGER.debug(f"... and prioritySoc also in self.data")
            #     else:
            #         _LOGGER.debug(f"... but prioritySoc NOT IN self.data {self.data}")
            # else:
            #     _LOGGER.debug(f"... and self.data is None?!")

            return result

        except UpdateFailed as exception:
            _LOGGER.warning(f"UpdateFailed: {exception}")
            raise UpdateFailed() from exception
        except Exception as other:
            _LOGGER.warning(f"UpdateFailed unexpected: {other}")
            raise UpdateFailed() from other

    def read_tag(self, tag: Tag, idx: int = None):
        ret = None
        if self.data is not None:
            if tag.type == EP_TYPE.LOADPOINTS:
                ret = self.read_tag_loadpoint(tag=tag, loadpoint_idx=idx)
            elif tag.type == EP_TYPE.VEHICLES:
                ret = self.read_tag_vehicle_int(tag=tag, loadpoint_idx=idx)
            elif tag.type == EP_TYPE.SITE:
                if tag.key in self.data:
                    ret = self.data[tag.key]
            elif tag.type == EP_TYPE.STATISTICS:
                ret = self.read_tag_statistics(tag=tag)
        # _LOGGER.debug(f"read from {tag.key} [@idx {idx}] -> {ret}")
        return ret

    def read_tag_statistics(self, tag: Tag):
        if JSONKEY_STATISTICS in self.data:
            if tag.subtype in self.data[JSONKEY_STATISTICS]:
                if tag.key in self.data[JSONKEY_STATISTICS][tag.subtype]:
                    return self.data[JSONKEY_STATISTICS][tag.subtype][tag.key]

    def read_tag_loadpoint(self, tag: Tag, loadpoint_idx: int = None):
        if loadpoint_idx is not None and len(self.data[JSONKEY_LOADPOINTS]) > loadpoint_idx - 1:
            # if tag == Tag.CHARGECURRENTS:
            #    _LOGGER.error(f"valA? {self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]}")
            #    _LOGGER.error(f"valB? {self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][tag.key]}")
            if tag.key in self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]:
                value = self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][tag.key]
                if tag == Tag.PLANTIME:
                    value = self._convert_time(value)
                return value

    def read_tag_vehicle_int(self, tag: Tag, loadpoint_idx: int = None):
        if len(self.data) > 0 and JSONKEY_LOADPOINTS in self.data and loadpoint_idx is not None:
            try:
                if len(self.data[JSONKEY_LOADPOINTS]) > loadpoint_idx - 1:
                    if Tag.VEHICLENAME.key in self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]:
                        vehicle_id = self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][Tag.VEHICLENAME.key]
                        if vehicle_id is not None:
                            if len(vehicle_id) > 0:
                                return self.read_tag_vehicle_str(tag=tag, vehicle_id=vehicle_id)
                            else:
                                # NO logging of empty vehicleName's -> since this just means no vehicle connected to
                                # the loadpoint...
                                pass
                        else:
                            _LOGGER.debug(f"read_tag_vehicle_int: vehicle_id is None for: {loadpoint_idx}")
                    else:
                        _LOGGER.debug(
                            f"read_tag_vehicle_int: {Tag.VEHICLENAME.key} not in {self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]} for: {loadpoint_idx}")
                else:
                    _LOGGER.debug(
                        f"read_tag_vehicle_int: len of 'loadpoints' {len(self.data[JSONKEY_LOADPOINTS])} - requesting: {loadpoint_idx}")

            except Exception as err:
                _LOGGER.info(f"read_tag_vehicle_int: could not find a connected vehicle at loadpoint: {loadpoint_idx}")

        return None

    def read_tag_vehicle_str(self, tag: Tag, vehicle_id: str):
        is_veh_PLANSSOC = tag == Tag.VEHICLEPLANSSOC
        is_veh_PLANSTIME = tag == Tag.VEHICLEPLANSTIME
        if is_veh_PLANSSOC or is_veh_PLANSTIME:
            # yes this is really a hack!
            if JSONKEY_PLANS in self.data[JSONKEY_VEHICLES][vehicle_id] and len(
                    self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLANS]) > 0:
                if is_veh_PLANSSOC:
                    value = self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLANS][0][JSONKEY_PLANS_SOC]
                    return str(int(value))  # float(int(value))/100
                elif is_veh_PLANSTIME:
                    return self._convert_time(
                        self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLANS][0][JSONKEY_PLANS_TIME])
            else:
                return None
        else:
            if tag.key in self.data[JSONKEY_VEHICLES][vehicle_id]:
                return self.data[JSONKEY_VEHICLES][vehicle_id][tag.key]
            else:
                return "0"

    async def async_write_plan(self, write_to_vehicle: bool, loadpoint_idx: str, soc: str, rfcdate: str):
        if write_to_vehicle:
            return await self.bridge.write_vehicle_plan_for_loadpoint_index(loadpoint_idx, soc, rfcdate)
        else:
            return await self.bridge.write_loadpoint_plan(loadpoint_idx, soc, rfcdate)

    async def async_press_tag(self, tag: Tag, value, idx: str = None, entity: Entity = None) -> dict:
        result = await self.bridge.press_tag(tag, value, idx)
        _LOGGER.debug(f"press result: {result}")

        if entity is not None:
            entity.async_schedule_update_ha_state(force_refresh=True)

        return result

    async def async_write_tag(self, tag: Tag, value, idx_str: str = None, entity: Entity = None) -> dict:
        """Update single data"""
        idx = int(idx_str)
        result = await self.bridge.write_tag(tag, value, idx_str)
        _LOGGER.debug(f"write result: {result}")

        if tag.key not in result or result[tag.key] is None:
            _LOGGER.info(f"could not write value: '{value}' to: {tag} result was: {result}")
        else:
            # IMH0 it's quite tricky to patch the self.data object here... but we try!
            if tag.type == EP_TYPE.SITE:
                if tag.key in self.data:
                    self.data[tag.key] = value

            elif tag.type == EP_TYPE.LOADPOINTS:
                if idx is not None and len(self.data[JSONKEY_LOADPOINTS]) > idx - 1:
                    if tag.key in self.data[JSONKEY_LOADPOINTS][idx - 1]:
                        self.data[JSONKEY_LOADPOINTS][idx - 1][tag.key] = value

            elif tag.type == EP_TYPE.VEHICLES:
                # TODO ?!
                _LOGGER.debug(f"{tag} no data update!")
                pass

        if entity is not None:
            _LOGGER.debug(f"schedule update...")
            entity.async_schedule_update_ha_state(force_refresh=True)

        return result

    @staticmethod
    def _convert_time(value: str):
        if value is not None and len(value) > 0:
            if "0001-01-01T00:00:00Z" == value:
                return None

            # we need to convert UTC in local time
            value = value.replace("Z", "+00:00")
            if ".000" in value:
                dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
            else:
                dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
            value = dt.astimezone().isoformat(sep=" ", timespec="minutes")
            return value.split("+")[0]
        else:
            return None

    @property
    def system_id(self):
        return self._system_id

    @property
    def currency(self):
        return self._currency

    @property
    def device_info_dict(self):
        return self._device_info_dict


class EvccBaseEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name_addon = None

    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: EntityDescription) -> None:
        if hasattr(description, "tag"):
            self.tag = description.tag
        else:
            self.tag = None

        self.idx = None
        if hasattr(description, "idx"):
            self.idx = description.idx
        else:
            self.idx = None

        if hasattr(description, "translation_key") and description.translation_key is not None:
            self._attr_translation_key = description.translation_key.lower()
        else:
            self._attr_translation_key = description.key.lower()

        if hasattr(description, "name_addon"):
            self._attr_name_addon = description.name_addon
        else:
            self._attr_name_addon = None

        if hasattr(description, "native_unit_of_measurement") and description.native_unit_of_measurement is not None:
            if "@@@" in description.native_unit_of_measurement:
                description.native_unit_of_measurement = description.native_unit_of_measurement.replace("@@@",
                                                                                                        coordinator.currency)

        self.entity_description = description
        self.coordinator = coordinator
        self.entity_id = f"{DOMAIN}.{self.coordinator.system_id}_{camel_to_snake(description.key)}"

    def _name_internal(self, device_class_name: str | None,
                       platform_translations: dict[str, Any], ) -> str | UndefinedType | None:

        tmp = super()._name_internal(device_class_name, platform_translations)
        if tmp is not None and "@@@" in tmp:
            tmp = tmp.replace("@@@", self.coordinator.currency)
        if self._attr_name_addon is not None:
            return f"{self._attr_name_addon} {tmp}"
        else:
            return tmp

    @property
    def device_info(self) -> dict:
        return self.coordinator.device_info_dict

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self.entity_id

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    async def async_update(self):
        """Update entity."""
        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self) -> bool:
        return False

    def _friendly_name_internal(self) -> str | None:
        """Return the friendly name.
        If has_entity_name is False, this returns self.name
        If has_entity_name is True, this returns device.name + self.name
        """
        name = self.name
        if name is UNDEFINED:
            name = None

        if not self.has_entity_name or not (device_entry := self.device_entry):
            return name

        device_name = device_entry.name_by_user or device_entry.name
        if name is None and self.use_device_name:
            return device_name

        # we overwrite the default impl here and just return our 'name'
        # return f"{device_name} {name}" if device_name else name
        if device_entry.name_by_user is not None:
            return f"{device_entry.name_by_user} {name}" if device_name else name
        elif self.coordinator.include_evcc_prefix:
            return f"[evcc] {name}"
        else:
            return name
