import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from packaging.version import Version

from custom_components.evcc_intg.pyevcc_ha import EvccApiBridge, TRANSLATIONS
from custom_components.evcc_intg.pyevcc_ha.const import (
    JSONKEY_LOADPOINTS,
    JSONKEY_VEHICLES,
    JSONKEY_PLAN,
    JSONKEY_PLANS,
    JSONKEY_PLANS_SOC,
    JSONKEY_PLANS_TIME,
    JSONKEY_STATISTICS,
    JSONKEY_STATISTICS_TOTAL,
    JSONKEY_STATISTICS_THISYEAR,
    JSONKEY_STATISTICS_365D,
    JSONKEY_STATISTICS_30D,
    ADDITIONAL_ENDPOINTS_DATA_TARIFF,
)
from custom_components.evcc_intg.pyevcc_ha.keys import Tag, EP_TYPE, camel_to_snake
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, Event, SupportsResponse, CoreState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry, config_validation as config_val, device_registry as device_reg
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.event import async_track_time_interval
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
    CONF_INCLUDE_EVCC,
    CONF_USE_WS
)
from .service import EvccService

_LOGGER: logging.Logger = logging.getLogger(__package__)

SCAN_INTERVAL = timedelta(seconds=10)
WEBSOCKET_WATCHDOG_INTERVAL: Final = timedelta(seconds=60)

CONFIG_SCHEMA = config_val.removed(DOMAIN, raise_if_present=False)

DEVICE_REG_CLEANUP_RUNNING = False

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
        pass
        # ok we could initially connect to the evcc...

    # If Home Assistant is already in a running state, start the watchdog
    # immediately, else trigger it after Home Assistant has finished starting.
    if(coordinator.use_ws):
        if hass.state is CoreState.running:
            await coordinator.start_watchdog()
        else:
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, coordinator.start_watchdog)

    # now we can initialize our coordinator with the data already read...
    await coordinator.read_evcc_config_on_startup(hass)

    # then we can start the entity registrations...
    hass.data[DOMAIN][config_entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if config_entry.state != ConfigEntryState.LOADED:
        config_entry.add_update_listener(async_reload_entry)

    # initialize our service...
    evcc_services = EvccService(hass, config_entry, coordinator)
    hass.services.async_register(DOMAIN, SERVICE_SET_LOADPOINT_PLAN, evcc_services.set_loadpoint_plan,
                                 supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SET_VEHICLE_PLAN, evcc_services.set_vehicle_plan,
                                 supports_response=SupportsResponse.OPTIONAL)

    # Do we need to patch something?!
    # if coordinator.check_for_max_of_16a:
    #     asyncio.create_task(coordinator.check_for_16a_limit(hass, config_entry.entry_id))

    # yes - hurray! we can now cleanup the device registry...
    asyncio.create_task(check_device_registry(hass))

    # ok we are done...
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    if unload_ok:
        if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][config_entry.entry_id]
            coordinator.stop_watchdog()
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


@staticmethod
async def check_device_registry(hass: HomeAssistant):
    global DEVICE_REG_CLEANUP_RUNNING
    if not DEVICE_REG_CLEANUP_RUNNING:
        DEVICE_REG_CLEANUP_RUNNING = True
        completed = False
        _LOGGER.debug(f"check device registry for outdated {DOMAIN} devices...")
        if hass is not None:
            a_device_reg = device_reg.async_get(hass)
            if a_device_reg is not None:
                key_list = []
                for a_device_entry in list(a_device_reg.devices.values()):
                    if hasattr(a_device_entry, "identifiers"):
                        ident_value = a_device_entry.identifiers
                        if f"{ident_value}".__contains__(DOMAIN):
                            if hasattr(a_device_entry, "manufacturer"):
                                manufacturer_value = a_device_entry.manufacturer
                                if not f"{manufacturer_value}".__eq__(MANUFACTURER):
                                    _LOGGER.info(f"found a OLD {DOMAIN} DeviceEntry: {a_device_entry}")
                                    key_list.append(a_device_entry.id)

                if len(key_list) > 0:
                    _LOGGER.info(f"NEED TO DELETE old {DOMAIN} DeviceEntries: {key_list}")
                    for a_device_entry_id in key_list:
                        a_device_reg.async_remove_device(device_id=a_device_entry_id)

                completed = True

        DEVICE_REG_CLEANUP_RUNNING = completed

class EvccDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry):
        _LOGGER.debug(f"starting evcc_intg for: options: {config_entry.options}\n data:{config_entry.data}")
        lang = hass.config.language.lower()
        self.name = config_entry.title
        self.use_ws = config_entry.options.get(CONF_USE_WS, config_entry.data.get(CONF_USE_WS, True))

        self.bridge = EvccApiBridge(host=config_entry.options.get(CONF_HOST, config_entry.data.get(CONF_HOST)),
                                    web_session=async_get_clientsession(hass),
                                    coordinator=self,
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

        # config_entry required to be able to launch watchdog in config_entry context
        self._config_entry = config_entry

        # attribute creation
        self._cost_type = None
        self._currency = "€"
        self._device_info_dict = {}
        self._loadpoint = {}
        self._vehicle = {}
        self._version = None
        self._grid_data_as_object = False

        self._watchdog = None

        # when we use the websocket we need to call the super constructor without update_interval...
        if self.use_ws:
            super().__init__(hass, _LOGGER, name=DOMAIN)
        else:
            super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    # Callable[[Event], Any]
    def __call__(self, evt: Event) -> bool:
        _LOGGER.debug(f"Event arrived: {evt}")
        return True

    async def start_watchdog(self, event=None):
        """Start websocket watchdog."""
        await self._async_watchdog_check()
        self._watchdog = async_track_time_interval(
            self.hass,
            self._async_watchdog_check,
            WEBSOCKET_WATCHDOG_INTERVAL,
        )

    def stop_watchdog(self):
        if hasattr(self, "_watchdog") and self._watchdog is not None:
            self._watchdog()

    async def _async_watchdog_check(self, *_):
        """Reconnect the websocket if it fails."""
        if not self.bridge.ws_connected:
            _LOGGER.info(f"Watchdog: websocket connect required")
            self._config_entry.async_create_background_task(self.hass, self.bridge.connect_ws(), "ws_connection")
        else:
            if self.bridge.request_tariff_endpoints:
                _LOGGER.debug(f"Watchdog: websocket is connected - check for optional required 'tariffs' updates")
                await self.bridge.ws_update_tariffs_if_required()
            else:
                _LOGGER.debug(f"Watchdog: websocket is connected")

    def clear_data(self):
        _LOGGER.debug(f"clear_data called...")
        self.bridge.clear_data()
        self.data.clear()

    async def read_evcc_config_on_startup(self, hass: HomeAssistant):
        # we will fetch th config from evcc:
        # b) vehicles
        # a) how many loadpoints
        # c) load point configuration (like 1/3 phase options)
        if (len(self.bridge._data) == 0 or
                Tag.VERSION.key not in self.bridge._data or
                JSONKEY_LOADPOINTS not in self.bridge._data or
                JSONKEY_VEHICLES not in self.bridge._data):
            await self.bridge.read_all_data()

        initdata = self.bridge._data
        if Tag.VERSION.key in initdata:
            self._version = initdata[Tag.VERSION.key]
        elif Tag.AVAILABLEVERSION.key in initdata:
            self._version = initdata[Tag.AVAILABLEVERSION.key]

        # something I just learned - the 'identifiers' is a LIST of keys which are used to identify one device...
        # e.g. if the identifiers contains just the 'domain', then all instance (config_entries) will be shown
        # together in the device registry... [which just sucks!]
        # Please note, that the identifiers object must be a (...)
        # for the 'unique_device_id' we will use the initial specified HOST/IP (if it will be later overwritten with
        # a changed host, we're going still use the initial one)
        unique_device_id = slugify(f"did_{self._config_entry.data.get(CONF_HOST)}")
        self._device_info_dict = {
            "identifiers": {(DOMAIN, unique_device_id)},
            "manufacturer": MANUFACTURER,
            "name": f"{NAME} [{self._system_id}]",
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
            phase_switching_supported = False
            if "chargerPhases1p3p" in a_loadpoint:
                phase_switching_supported = a_loadpoint["chargerPhases1p3p"]
            elif "chargerPhaseSwitching" in a_loadpoint:
                phase_switching_supported = a_loadpoint["chargerPhaseSwitching"]
            else:
                phase_switching_supported = False

            self._loadpoint[f"{api_index}"] = {
                "name": a_loadpoint["title"],
                "id": slugify(a_loadpoint["title"]),
                "has_phase_auto_option": phase_switching_supported,
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

        _version_info = None
        if Tag.VERSION.key in initdata:
            _version_info = initdata[Tag.VERSION.key]
            # we need to check for possible NightlyBuild tags in the Version key
            if " (" in _version_info:
                _version_info = _version_info.split(" (")[0].strip()

        # here we have an issue, when there is no grid data
        # available (or is no object) at system start....
        if "grid" in initdata and initdata["grid"] is not None and isinstance(initdata["grid"], (dict, list)):
            if ("power" in initdata["grid"] or
                "currents" in initdata["grid"] or
                "energy" in initdata["grid"] or
                "powers" in initdata["grid"] ):
                self._grid_data_as_object = True
        elif _version_info is not None:
            if Version(_version_info) >= Version("0.133.0"):
                self._grid_data_as_object = True

        # enable the additional tariff endpoints...
        if _version_info is not None:
            _LOGGER.debug(f"check for tariff endpoints... {_version_info}")
            if Version(_version_info) >= Version("0.200.0"):
                request_tariff_keys = []

                # we must check, if the tariff entities are enabled...
                if hass is not None:
                    registry = entity_registry.async_get(hass)
                    if registry is not None:
                        entity_id = f"sensor.{self._system_id}_{Tag.TARIF_GRID.entity_key}".lower()
                        a_entity = registry.async_get(entity_id)
                        if a_entity is not None and a_entity.disabled_by is None:
                            _LOGGER.info("***** QUERY_TARIF_GRID ********")
                            request_tariff_keys.append(Tag.TARIF_GRID.key)

                        entity_id = f"sensor.{self._system_id}_{Tag.TARIF_SOLAR.entity_key}".lower()
                        a_entity = registry.async_get(entity_id)
                        if a_entity is not None and a_entity.disabled_by is None:
                            _LOGGER.info("***** QUERY_TARIF_SOLAR ********")
                            request_tariff_keys.append(Tag.TARIF_SOLAR.key)

                if len(request_tariff_keys) > 0:
                    self.bridge.enable_tariff_endpoints(request_tariff_keys)
                    # make sure, that the tariff data is up-to-date...
                    await self.bridge.read_all_data(only_tariffs=True)
        # else:
        #     _LOGGER.debug(f"no version available... {initdata}")
        #     for a_key in initdata:
        #         _LOGGER.error(f"key: {a_key}")

        _LOGGER.debug(
            f"read_evcc_config: Use Websocket: {self.use_ws} (already started? {self.bridge.ws_connected}) LPs: {len(self._loadpoint)} VEHs: {len(self._vehicle)} CT: '{self._cost_type}' CUR: {self._currency} GAO: {self._grid_data_as_object}")

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        try:
            if self.bridge.ws_connected:
                _LOGGER.info("_async_update_data called (but websocket is active - no data will be requested!)")
                return self.bridge._data
            else:
                _LOGGER.debug(f"_async_update_data called")
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

                    # checking for possible existing subtypes (so key is just a 'container' for the real value)
                    # (elsewhere we solve this right now via entity_description.array_idx) -> we must check, if
                    # this can't be also used here ?!
                    #if tag.subtype is not None and isinstance(ret, dict):
                    #    if tag.subtype in ret:
                    #        ret = ret[tag.subtype]
                    #    else:
                    #        ret = None

            elif tag.type == EP_TYPE.STATISTICS:
                ret = self.read_tag_statistics(tag=tag)
            elif tag.type == EP_TYPE.TARIFF:
                ret = self.read_tag_tariff(tag=tag)
        # _LOGGER.debug(f"read from {tag.key} [@idx {idx}] -> {ret}")
        return ret

    def read_tag_tariff(self, tag: Tag):
        if ADDITIONAL_ENDPOINTS_DATA_TARIFF in self.data:
            if tag.key in self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF]:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF][tag.key]

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

                if tag == Tag.PLANTIME or tag == Tag.EFFECTIVEPLANTIME:
                    value = self._convert_time(value)

                elif tag == Tag.PLANPROJECTEDSTART or tag == Tag.PLANPROJECTEDEND:
                    # the API already return a ISO 8601 'date' here - but we need to convert it to a datetime object
                    # so that it then can be finally converted by the default Sensor to a ISO 8601 date...
                    value = self._convert_time(value)

                elif tag == Tag.PVREMAINING:
                    # the API just return seconds here - but we need to convert it to a datetime object so actually
                    # the value is 'now' + seconds...
                    if value != 0:
                        value = datetime.now(timezone.utc) + timedelta(seconds=value)
                    else:
                        value = None

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
            # yes this is really a hack! [at a certain point the API just returned 'plan' and 'plans' have been removed] ?!
            if JSONKEY_PLAN in self.data[JSONKEY_VEHICLES][vehicle_id] and len(self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLAN]) > 0:
                if is_veh_PLANSSOC:
                    value = self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLAN][JSONKEY_PLANS_SOC]
                    return str(int(value))  # float(int(value))/100
                elif is_veh_PLANSTIME:
                    return self._convert_time(self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLAN][JSONKEY_PLANS_TIME])
            elif JSONKEY_PLANS in self.data[JSONKEY_VEHICLES][vehicle_id] and len(self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLANS]) > 0:
                if is_veh_PLANSSOC:
                    value = self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLANS][0][JSONKEY_PLANS_SOC]
                    return str(int(value))  # float(int(value))/100
                elif is_veh_PLANSTIME:
                    return self._convert_time(self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLANS][0][JSONKEY_PLANS_TIME])
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

        if entity is not None and not self.bridge.ws_connected:
            entity.async_schedule_update_ha_state(force_refresh=True)

        return result

    async def async_write_tag(self, tag: Tag, value, idx_str: str = None, entity: Entity = None) -> dict:
        """Update single data"""
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
                if idx_str is not None:
                    idx = int(idx_str)
                    if len(self.data[JSONKEY_LOADPOINTS]) > idx - 1:
                        if tag.key in self.data[JSONKEY_LOADPOINTS][idx - 1]:
                            self.data[JSONKEY_LOADPOINTS][idx - 1][tag.key] = value

            elif tag.type == EP_TYPE.VEHICLES:
                # TODO ?!
                _LOGGER.debug(f"{tag} no data update!")
                pass

        if entity is not None and not self.bridge.ws_connected:
            _LOGGER.debug(f"schedule update...")
            entity.async_schedule_update_ha_state(force_refresh=True)

        return result

    @staticmethod
    def _convert_time(value):
        if value is not None:
            value = str(value)
            if len(value) > 0:
                if "0001-01-01T00:00:00Z" == value:
                    return None

                return datetime.fromisoformat(value)

            return None
        else:
            return None

    @staticmethod
    def _convert_time_old(value: str):
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
    def system_id(self) -> str:
        return self._system_id

    @property
    def currency(self) -> str:
        return self._currency

    @property
    def device_info_dict(self) -> dict:
        return self._device_info_dict

    @property
    def grid_data_as_object(self) -> bool:
        return self._grid_data_as_object


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
