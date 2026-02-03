import asyncio
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Final

import aiohttp
from aiohttp import ClientConnectionError
from packaging.version import Version

from custom_components.evcc_intg.pyevcc_ha import EvccApiBridge
from custom_components.evcc_intg.pyevcc_ha.const import (
    TRANSLATIONS,
    JSONKEY_LOADPOINTS,
    JSONKEY_VEHICLES,
    JSONKEY_PLAN,
    JSONKEY_PLANS_DEPRECATED,
    JSONKEY_PLAN_SOC,
    JSONKEY_PLAN_TIME,
    JSONKEY_STATISTICS,
    JSONKEY_STATISTICS_TOTAL,
    JSONKEY_STATISTICS_THISYEAR,
    JSONKEY_STATISTICS_365D,
    JSONKEY_STATISTICS_30D,
    ADDITIONAL_ENDPOINTS_DATA_TARIFF,
    ADDITIONAL_ENDPOINTS_DATA_SESSIONS,
    SESSIONS_KEY_LOADPOINTS,
    SESSIONS_KEY_VEHICLES, JSONKEY_CIRCUITS
)
from custom_components.evcc_intg.pyevcc_ha.keys import Tag, EP_TYPE, camel_to_snake
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, Event, SupportsResponse, CoreState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry, config_validation as config_val, device_registry as device_reg
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import UNDEFINED, UndefinedType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify
from .const import (
    NAME,
    NAME_SHORT,
    DOMAIN,
    MANUFACTURER,
    PLATFORMS,
    STARTUP_MESSAGE,
    SERVICE_SET_LOADPOINT_PLAN,
    SERVICE_SET_VEHICLE_PLAN,
    SERVICE_DEL_LOADPOINT_PLAN,
    SERVICE_DEL_VEHICLE_PLAN,
    CONF_INCLUDE_EVCC,
    CONF_USE_WS,
    CONF_PURGE_ALL,
    CONFIG_VERSION,
    CONFIG_MINOR_VERSION,
    EVCC_JSON_KEY_NAME,
    EVCC_JSON_ORIGIN_OBJECT
)
from .service import EvccService

_LOGGER: logging.Logger = logging.getLogger(__package__)

SCAN_INTERVAL = timedelta(seconds=10)
WEBSOCKET_WATCHDOG_INTERVAL: Final = timedelta(seconds=60)

CONFIG_SCHEMA = config_val.removed(DOMAIN, raise_if_present=False)

DEVICE_REG_CLEANUP_RUNNING = False


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    if config_entry.version < CONFIG_VERSION:
        if config_entry.data is not None and len(config_entry.data) > 0:
            _LOGGER.debug(f"Migrating configuration from version {config_entry.version}.{config_entry.minor_version}")

            if config_entry.options is not None and len(config_entry.options):
                new_data = {**config_entry.data, **config_entry.options}
            else:
                new_data = config_entry.data

            hass.config_entries.async_update_entry(config_entry, data=new_data, options={}, version=CONFIG_VERSION, minor_version=CONFIG_MINOR_VERSION)
            _LOGGER.debug(f"Migration to configuration version {config_entry.version}.{config_entry.minor_version} successful")
    return True


async def async_setup(hass: HomeAssistant, config: dict):  # pylint: disable=unused-argument
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug(f"async_setup_entry(): called")

    if DOMAIN not in hass.data:
        the_integration = await async_get_integration(hass, DOMAIN)
        intg_version = the_integration.version if the_integration is not None else "UNKNOWN"
        _LOGGER.info(STARTUP_MESSAGE % intg_version)
        hass.data.setdefault(DOMAIN, {"manifest_version": intg_version})

    # yes - hurray! we can now cleanup the device registry...
    purge_all_devices = config_entry.data.get(CONF_PURGE_ALL, False)
    asyncio.create_task(check_device_registry(hass, purge_all_devices, config_entry.entry_id))
    if purge_all_devices:
        # we remove the 'purge_all_devices' flag from the config entry...
        new_data_dict = config_entry.data.copy()
        del new_data_dict[CONF_PURGE_ALL]
        hass.config_entries.async_update_entry(config_entry, data=new_data_dict, options={}, version=CONFIG_VERSION, minor_version=CONFIG_MINOR_VERSION)
        _LOGGER.debug(f"Updated configuration (PURGE_ALL removed): {new_data_dict}")

    # using the same http client for test and final integration...
    http_session = async_get_clientsession(hass)

    # simple check, IF the evcc serve is up and running ... raise an 'ConfigEntryNotReady' if
    # the configured backend could not be reached - then let HA deal with an optional retry
    await check_evcc_is_available(http_session, config_entry)

    coordinator = EvccDataUpdateCoordinator(hass, http_session, config_entry)
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady
    else:
        # If Home Assistant is already in a running state, start the watchdog
        # immediately, else trigger it after Home Assistant has finished starting.
        if coordinator.use_ws:
            if hass.state is CoreState.running:
                await coordinator.start_watchdog()
            else:
                hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, coordinator.start_watchdog)

        # now we can attempt to initialize our coordinator with the data already read...
        if not await coordinator.read_evcc_config_on_startup(hass):
            _LOGGER.warning(f"coordinator.read_evcc_config_on_startup() was not completed successfully - please enable debug-log option in order to find a posiible root cause.")

        # then we can start the entity registrations...
        hass.data[DOMAIN][config_entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

        # initialize our service...
        evcc_services = EvccService(hass, config_entry, coordinator)
        hass.services.async_register(DOMAIN, SERVICE_SET_LOADPOINT_PLAN, evcc_services.set_loadpoint_plan,
                                     supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, SERVICE_SET_VEHICLE_PLAN, evcc_services.set_vehicle_plan,
                                     supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, SERVICE_DEL_LOADPOINT_PLAN, evcc_services.del_loadpoint_plan,
                                     supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, SERVICE_DEL_VEHICLE_PLAN, evcc_services.del_vehicle_plan,
                                     supports_response=SupportsResponse.OPTIONAL)

        config_entry.async_on_unload(config_entry.add_update_listener(entry_update_listener))
        # ok we are done...
        return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    _LOGGER.debug(f"async_unload_entry() called for entry: {config_entry.entry_id}")
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    if unload_ok:
        if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][config_entry.entry_id]
            coordinator.stop_watchdog()
            coordinator.clear_data()
            hass.data[DOMAIN].pop(config_entry.entry_id)

        hass.services.async_remove(DOMAIN, SERVICE_SET_LOADPOINT_PLAN)
        hass.services.async_remove(DOMAIN, SERVICE_SET_VEHICLE_PLAN)
        hass.services.async_remove(DOMAIN, SERVICE_DEL_LOADPOINT_PLAN)
        hass.services.async_remove(DOMAIN, SERVICE_DEL_VEHICLE_PLAN)

    return unload_ok


async def entry_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update the configuration of the host entity."""
    _LOGGER.debug(f"entry_update_listener() called for entry: {config_entry.entry_id}")
    await hass.config_entries.async_reload(config_entry.entry_id)


@staticmethod
async def check_evcc_is_available(http_session: aiohttp.ClientSession, config_entry: ConfigEntry) -> None:
    a_host = config_entry.data.get(CONF_HOST, "NOT-CONFIGURED")
    try:
        bridge = EvccApiBridge(host=a_host, web_session=http_session)
        await bridge.is_evcc_available()
        return True

    except Exception as err:
        raise ConfigEntryNotReady(f"evcc instance '{a_host}' not available (yet) - HA will keep trying") from err


@staticmethod
async def check_device_registry(hass: HomeAssistant, purge_all: bool = False, config_entry_id:str = None) -> None:
    global DEVICE_REG_CLEANUP_RUNNING
    if not DEVICE_REG_CLEANUP_RUNNING:
        DEVICE_REG_CLEANUP_RUNNING = True
        _LOGGER.debug(f"check device registry for outdated {DOMAIN} devices...")
        if hass is not None:
            a_device_reg = device_reg.async_get(hass)
            if a_device_reg is not None:
                devices_to_delete = []
                for a_device_entry in list(a_device_reg.devices.values()):
                    if hasattr(a_device_entry, "identifiers"):
                        ident_value = a_device_entry.identifiers

                        if f"{ident_value}".__contains__(DOMAIN):

                            if purge_all and config_entry_id is not None:
                                if config_entry_id in a_device_entry.config_entries:
                                    devices_to_delete.append(a_device_entry.id)

                            elif hasattr(a_device_entry, "manufacturer"):
                                manufacturer_value = a_device_entry.manufacturer
                                if not f"{manufacturer_value}".__eq__(MANUFACTURER):
                                    _LOGGER.info(f"found a OLD {DOMAIN} DeviceEntry: {a_device_entry}")
                                    devices_to_delete.append(a_device_entry.id)

                            #elif intg_version != "UNKNOWN":
                            #    if not f"{ident_value}".__contains__(intg_version):
                            #        devices_to_delete.append(a_device_entry.id)

                if len(devices_to_delete) > 0:
                    devices_to_delete = list(dict.fromkeys(devices_to_delete))
                    if purge_all:
                        _LOGGER.info(f"CLEAN ALL {DOMAIN} DeviceEntries: {devices_to_delete}")
                    else:
                        _LOGGER.info(f"NEED TO DELETE old {DOMAIN} DeviceEntries: {devices_to_delete}")

                    for a_device_entry_id in devices_to_delete:
                        a_device_reg.async_remove_device(device_id=a_device_entry_id)

        DEVICE_REG_CLEANUP_RUNNING = False


class EvccDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, http_session: aiohttp.ClientSession, config_entry):
        _LOGGER.debug(f"starting evcc_intg for: data:{config_entry.data}")
        self.name = config_entry.title
        self.use_ws = config_entry.data.get(CONF_USE_WS, True)

        lang = hass.config.language.lower()
        if lang in TRANSLATIONS:
            self.lang_map = TRANSLATIONS[lang]
        else:
            self.lang_map = TRANSLATIONS["en"]

        self.bridge = EvccApiBridge(host=config_entry.data.get(CONF_HOST, "NOT-CONFIGURED"),
                                    web_session=http_session,
                                    coordinator=self,
                                    lang=lang)

        global SCAN_INTERVAL
        SCAN_INTERVAL = timedelta(seconds=config_entry.data.get(CONF_SCAN_INTERVAL, 5))

        self.include_evcc_prefix = config_entry.data.get(CONF_INCLUDE_EVCC, False)

        # we want some sort of unique identifier that can be selected by the user
        # during the initial configuration phase
        self._system_id = slugify(config_entry.title)

        # config_entry required to be able to launch watchdog in config_entry context
        self._config_entry = config_entry

        # attribute creation
        self._cost_type = None
        self._currency = "€"
        self._device_info_dict = {}
        self._circuit = {}
        self._loadpoint = {}
        self._vehicle = {}
        self._version = None
        self._grid_data_as_object = False
        self._battery_data_as_object = False
        self._watchdog = None

        # a global store for entities that we must manipulate later on...
        self.select_entities_dict = {}

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
        self._watchdog = async_track_time_interval(self.hass, self._async_watchdog_check, WEBSOCKET_WATCHDOG_INTERVAL)

    def stop_watchdog(self):
        if hasattr(self, "_watchdog") and self._watchdog is not None:
            self._watchdog()

    async def _async_watchdog_check(self, *_):
        """Reconnect the websocket if it fails."""
        if len(self._device_info_dict) == 0:
            # when 'self._device_info_dict' is still {}, then the integration was started, but the
            # evcc server was not yet available and the read_evcc_config_on_startup function was
            # not called yet...
            _LOGGER.info(f"Watchdog: Integration not READY - no device info available yet")
        else:
            if not self.bridge.ws_connected:
                _LOGGER.info(f"Watchdog: websocket connect required")
                self._config_entry.async_create_background_task(self.hass, self.bridge.connect_ws(), "ws_connection")
            else:
                if self.bridge.request_tariff_endpoints:
                    _LOGGER.debug(f"Watchdog: websocket is connected - check for optional required 'tariffs' updates")
                    await self.bridge.ws_update_tariffs_if_required()

                _LOGGER.debug(f"Watchdog: websocket is connected - check for optional required 'sessions' updates")
                await self.bridge.ws_update_sessions_if_required()

                _LOGGER.debug(f"Watchdog: websocket is connected")

    def clear_data(self):
        _LOGGER.debug(f"clear_data called...")
        self.bridge.clear_data()
        self.data.clear()

    async def read_evcc_config_on_startup(self, hass: HomeAssistant):
        # we will fetch the config from evcc:
        # b) vehicles
        # a) how many loadpoints
        # c) load point configuration (like 1/3 phase options)
        if self.bridge._data is None or (len(self.bridge._data) == 0 or Tag.VERSION.json_key not in self.bridge._data or JSONKEY_LOADPOINTS not in self.bridge._data or JSONKEY_VEHICLES not in self.bridge._data):
            await self.bridge.read_all_data()

        initdata = self.bridge._data

        if initdata is None or len(initdata) == 0:
            _LOGGER.warning("read_evcc_config_on_startup(): could not init evcc_intg - no data available from evcc!")
            return False

        if Tag.VERSION.json_key in initdata:
            self._version = initdata[Tag.VERSION.json_key]
        else:
            self._version = "UNKNOWN"

        # Something I just learned - the 'identifiers' is a LIST of keys which are used to identify one device...
        # E.g., if the identifiers contain just the 'domain', then all instances (config_entries) will be shown
        # together in the device registry... [which just sucks!]
        # Please note, that the identifiers object must be a (...)
        # for the 'unique_device_id' we will use the initial specified HOST/IP (if it is later overwritten with
        # a changed host, we're going still use the initial one)
        unique_device_id = slugify(f"did_{self._config_entry.data.get(CONF_HOST)}")
        self._device_info_dict = {
            "identifiers": {(DOMAIN, unique_device_id)},
            "manufacturer": MANUFACTURER,
            "name": f"{NAME} [{self._system_id}]",
            "sw_version": self._version
        }

        # init our circuits data... [this is a JSON DICT]
        if JSONKEY_CIRCUITS in initdata:
            for a_evcc_circuit_name in initdata[JSONKEY_CIRCUITS]:
                a_circuit_object = initdata[JSONKEY_CIRCUITS][a_evcc_circuit_name]
                self._circuit[a_evcc_circuit_name] = {
                    EVCC_JSON_KEY_NAME: a_evcc_circuit_name,
                    EVCC_JSON_ORIGIN_OBJECT: a_circuit_object
                }
        else:
            _LOGGER.debug(f"read_evcc_config_on_startup(): NO 'circuits' found [{JSONKEY_CIRCUITS}] in the evcc data: {initdata}")


        # init our vehicles data... [this is a JSON DICT]
        if JSONKEY_VEHICLES in initdata:
            for a_evcc_veh_name in initdata[JSONKEY_VEHICLES]:
                a_vehicle_object = initdata[JSONKEY_VEHICLES][a_evcc_veh_name]

                # we must remove all possible ':' chars (like from 'db:12' - since HA can't handle them
                # in the translation keys - be careful with this self._vehicle dict keys!
                # self._vehicle[a_evcc_veh_name.replace(':', '_')] = {
                self._vehicle[a_evcc_veh_name] = {
                    EVCC_JSON_KEY_NAME: a_evcc_veh_name,
                    EVCC_JSON_ORIGIN_OBJECT: a_vehicle_object,
                    "name": a_vehicle_object["title"],
                    "id": slugify(a_vehicle_object["title"]),
                    "capacity": a_vehicle_object["capacity"] if "capacity" in a_vehicle_object else None,
                    "minSoc": a_vehicle_object["minSoc"] if "minSoc" in a_vehicle_object else None,
                    "limitSoc": a_vehicle_object["limitSoc"] if "limitSoc" in a_vehicle_object else None
                }
        else:
            _LOGGER.warning(f"read_evcc_config_on_startup(): NO 'vehicles' found [{JSONKEY_VEHICLES}] in the evcc data: {initdata}")

        # init our loadpoints data... [but this is a LIST in JSON!!!]
        api_index = 1
        if JSONKEY_LOADPOINTS in initdata:
            for a_loadpoint_object in initdata[JSONKEY_LOADPOINTS]:
                single_phase_only = False
                if "chargerSinglePhase" in a_loadpoint_object:
                    single_phase_only = a_loadpoint_object["chargerSinglePhase"]

                phase_switching_supported = False
                if "chargerPhases1p3p" in a_loadpoint_object:
                    phase_switching_supported = a_loadpoint_object["chargerPhases1p3p"]
                elif "chargerPhaseSwitching" in a_loadpoint_object:
                    phase_switching_supported = a_loadpoint_object["chargerPhaseSwitching"]

                # we need to check if the charger is a heater or not...
                # effective_limit_soc, vehicle_soc, effective_plan_soc and others
                # currently only used in sensor.py
                is_heating = False
                if "chargerFeatureHeating" in a_loadpoint_object:
                    is_heating = a_loadpoint_object["chargerFeatureHeating"]

                is_integrated = False
                if "chargerFeatureIntegratedDevice" in a_loadpoint_object:
                    is_integrated = a_loadpoint_object["chargerFeatureIntegratedDevice"]

                self._loadpoint[f"{api_index}"] = {
                    EVCC_JSON_KEY_NAME: f"{api_index}",
                    EVCC_JSON_ORIGIN_OBJECT: a_loadpoint_object,
                    "name": a_loadpoint_object["title"],
                    "id": slugify(a_loadpoint_object["title"]),
                    "has_phase_auto_option": phase_switching_supported,
                    "only_single_phase": single_phase_only,
                    "is_heating": is_heating,
                    "is_integrated": is_integrated,
                    "vehicle_key": a_loadpoint_object["vehicleName"]
                }

                api_index += 1
        else:
            _LOGGER.warning(f"read_evcc_config_on_startup(): NO 'loadpoints' found [{JSONKEY_LOADPOINTS}] in the evcc data: {initdata}")


        if "smartCostType" in initdata:
            self._cost_type = initdata["smartCostType"]
        else:
            self._cost_type = "co2"

        if "currency" in initdata:
            self._currency = initdata["currency"]
            if self._currency == "EUR":
                self._currency = "€"

        _version_info = None
        _version_info_raw = None
        if Tag.VERSION.json_key in initdata:
            _version_info_raw = initdata[Tag.VERSION.json_key]
            # we need to check for possible NightlyBuild tags in the Version key
            if " (" in _version_info_raw:
                _version_info = _version_info_raw.split(" (")[0].strip()
            elif "-" in _version_info_raw:
                _version_info = _version_info_raw[:_version_info_raw.index('-')]
            else:
                _version_info = _version_info_raw

        # here we have an issue, when there is no grid data
        # available (or is no object) at system start....
        if "grid" in initdata and initdata["grid"] is not None and isinstance(initdata["grid"], (dict, list)):
            grid_obj = initdata["grid"]
            if ("power"     in grid_obj or
                "currents"  in grid_obj or
                "energy"    in grid_obj or
                "powers"    in grid_obj):
                self._grid_data_as_object = True
        elif _version_info is not None and len(_version_info) > 0:
            try:
                if Version(_version_info) >= Version("0.133.0"):
                    self._grid_data_as_object = True

            except BaseException as exc:
                _LOGGER.info(f"read_evcc_config_on_startup(): [1] Exception when trying handle _version_info: '{_version_info}' | raw version: '{_version_info_raw}'")

        # we must check, if the battery is just a ARRAY... or if it's a OBJECT
        if "battery" in initdata and initdata["battery"] is not None and isinstance(initdata["battery"], (dict, list)):
            batt_obj = initdata["battery"]
            if ("power"     in batt_obj or
                "capacity"  in batt_obj or
                "soc"       in batt_obj or
                "devices"   in batt_obj):
                self._battery_data_as_object = True
        elif _version_info is not None and len(_version_info) > 0:
            try:
                # TODO LATER: we don't know in which release the battery object will be
                # refactored... [so we keep this open right now]
                if Version(_version_info) >= Version("999.209.8"):
                    self._battery_data_as_object = True

            except BaseException as exc:
                _LOGGER.info(f"read_evcc_config_on_startup(): [2] Exception when trying handle _version_info: '{_version_info}' | raw version: '{_version_info_raw}'")



        # enable the additional tariff endpoints...
        try:
            if _version_info is not None and len(_version_info) > 0:
                _LOGGER.debug(f"check for tariff endpoints... {_version_info}")
                if Version(_version_info) >= Version("0.200.0"):
                    request_tariff_keys = []

                    # we must check, if the tariff entities are enabled...
                    if hass is not None:
                        registry = entity_registry.async_get(hass)
                        if registry is not None:
                            for a_tag in [Tag.TARIFF_API_GRID, Tag.TARIFF_API_SOLAR, Tag.TARIFF_API_FEEDIN, Tag.TARIFF_API_PLANNER]:
                                entity_id = f"sensor.{self._system_id}_{a_tag.entity_key}".lower()
                                a_entity = registry.async_get(entity_id)
                                if a_entity is not None and a_entity.disabled_by is None:
                                    _LOGGER.info(f"***** QUERY_{a_tag.json_key.upper()} ********")
                                    request_tariff_keys.append(a_tag.json_key)

                    if len(request_tariff_keys) > 0:
                        self.bridge.enable_tariff_endpoints(request_tariff_keys)
                        # make sure, that the tariff data is up-to-date...
                        await self.bridge.read_all_data(request_all=False, request_tariffs=True)
            # else:
            #     _LOGGER.debug(f"no version available... {initdata}")
            #     for a_key in initdata:
            #         _LOGGER.error(f"key: {a_key}")
        except BaseException as exc:
            _LOGGER.info(f"read_evcc_config_on_startup(): Exception when trying to query tariff endpoints - _version_info: '{_version_info}' | raw version: '{_version_info_raw}' - {type(exc).__name__} - {exc}")

        _LOGGER.debug(f"read_evcc_config_on_startup(): Use Websocket: {self.use_ws} (already started? {self.bridge.ws_connected}) LPs: {len(self._loadpoint)} VEHs: {len(self._vehicle)} CT: '{self._cost_type}' CUR: {self._currency} GridAsObject: {self._grid_data_as_object} BatteryAsObject: {self._battery_data_as_object}")
        return True

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        try:
            if self.bridge.ws_connected:
                _LOGGER.debug("_async_update_data called (but websocket is active - no data will be requested!)")
                return self.bridge._data
            else:
                _LOGGER.debug(f"_async_update_data called")
                # if self.data is not None:
                #    _LOGGER.debug(f"number of fields before query: {len(self.data)} ")
                # result = await self.bridge.read_all()
                # _LOGGER.debug(f"number of fields after query: {len(result)}")
                # return result

                result = await self.bridge.read_all_data()
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
        except ClientConnectionError as exception:
            _LOGGER.warning(f"UpdateFailed cause of ClientConnectionError: {exception}")
            raise UpdateFailed() from exception
        except Exception as other:
            _LOGGER.warning(f"UpdateFailed unexpected: {type(other)} - {other}")
            raise UpdateFailed() from other

    def read_tag(self, tag: Tag, idx: int = None):
        ret = None
        if self.data is not None:
            if tag.type == EP_TYPE.LOADPOINTS:
                ret = self.read_tag_loadpoint(tag=tag, loadpoint_idx=idx)

            elif tag.type == EP_TYPE.VEHICLES:
                ret = self.read_tag_vehicle_int(tag=tag, loadpoint_idx=idx)

            # in the case of circuits, the 'idx' is not a int - it is a str and this
            # str is the key in the circuits dict...
            elif tag.type == EP_TYPE.CIRCUITS and idx is not None:
                circuit_data = self.data.get(JSONKEY_CIRCUITS, {}).get(idx, {})
                ret = circuit_data.get(tag.json_key, None) if tag.json_key in circuit_data else None

            elif tag.type == EP_TYPE.SITE:
                if tag.json_key in self.data:
                    ret = self.data[tag.json_key]

                elif tag.json_key_alias is not None and tag.json_key_alias in self.data:
                    ret = self.data[tag.json_key_alias]

                elif tag.subtype is not None and tag.subtype in self.data:
                    a_obj = self.data[tag.subtype]
                    if isinstance(a_obj, dict) and len(a_obj) > 0:
                        if tag.json_key in a_obj:
                            ret = a_obj[tag.json_key]
                        elif tag.json_key_alias is not None and tag.json_key_alias in a_obj:
                            ret = a_obj[tag.json_key_alias]

            elif tag.type == EP_TYPE.EVOPT:
                ret = self.data.get(EP_TYPE.EVOPT.value, {}).get(tag.json_key, None)

            elif tag.type == EP_TYPE.STATISTICS:
                ret = self.read_tag_statistics(tag=tag)

            elif tag.type == EP_TYPE.TARIFF:
                ret = self.read_tag_tariff(tag=tag)
        # _LOGGER.debug(f"read from {tag.key} [@idx {idx}] -> {ret}")
        return ret

    def read_tag_tariff(self, tag: Tag):
        if ADDITIONAL_ENDPOINTS_DATA_TARIFF in self.data:
            if tag.json_key in self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF]:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF][tag.json_key]
            elif tag.json_key_alias is not None and tag.json_key_alias in self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF]:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF][tag.json_key_alias]

    def read_tag_sessions(self, tag: Tag, additional_key: str = None):
        if ADDITIONAL_ENDPOINTS_DATA_SESSIONS in self.data:
            if tag == Tag.CHARGING_SESSIONS:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS]
            elif tag == Tag.CHARGING_SESSIONS_VEHICLES:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_VEHICLES]
            elif tag == Tag.CHARGING_SESSIONS_LOADPOINTS:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_LOADPOINTS]

            elif tag.subtype is not None and tag.subtype in self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS]:
                # vehicles or loadpoints sub-tag ?
                a_dict = self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][tag.subtype]
                if additional_key is not None and additional_key in a_dict:
                    return a_dict[additional_key].get(tag.json_key, None)
                else:
                    return a_dict.get(tag.json_key, None)

    def read_tag_statistics(self, tag: Tag):
        if JSONKEY_STATISTICS in self.data:
            if tag.subtype in self.data[JSONKEY_STATISTICS]:
                if tag.json_key in self.data[JSONKEY_STATISTICS][tag.subtype]:
                    return self.data[JSONKEY_STATISTICS][tag.subtype][tag.json_key]
                elif tag.json_key_alias is not None and tag.json_key_alias in self.data[JSONKEY_STATISTICS]:
                    return self.data[JSONKEY_STATISTICS][tag.subtype][tag.json_key_alias]

    def read_tag_loadpoint(self, tag: Tag, loadpoint_idx: int = None):
        if loadpoint_idx is not None and len(self.data[JSONKEY_LOADPOINTS]) > loadpoint_idx - 1:
            # if tag == Tag.CHARGECURRENTS:
            #    _LOGGER.error(f"valA? {self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]}")
            #    _LOGGER.error(f"valB? {self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][tag.key]}")

            value = None
            if tag.json_key in self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]:
                value = self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][tag.json_key]
            elif tag.json_key_alias is not None and tag.json_key_alias in self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]:
                value = self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][tag.json_key_alias]

            if value is not None:
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
                    if Tag.LP_VEHICLENAME.json_key in self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]:
                        vehicle_id = self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][Tag.LP_VEHICLENAME.json_key]
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
                        _LOGGER.debug(f"read_tag_vehicle_int: {Tag.LP_VEHICLENAME.json_key} not in {self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]} for: {loadpoint_idx}")
                else:
                    _LOGGER.debug(f"read_tag_vehicle_int: len of 'loadpoints' {len(self.data[JSONKEY_LOADPOINTS])} - requesting: {loadpoint_idx}")

            except Exception as err:
                _LOGGER.info(f"read_tag_vehicle_int: could not find a connected vehicle at loadpoint: {loadpoint_idx}")

        return None

    def read_tag_vehicle_str(self, tag: Tag, vehicle_id: str):
        is_veh_PLANSSOC = tag == Tag.VEHICLEPLANSOC
        is_veh_PLANSTIME = tag == Tag.VEHICLEPLANTIME
        if is_veh_PLANSSOC or is_veh_PLANSTIME:
            # yes this is really a hack! [at a certain point the API just returned 'plan' and 'plans' have been removed] ?!
            if JSONKEY_PLAN in self.data[JSONKEY_VEHICLES][vehicle_id] and len(self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLAN]) > 0:
                if is_veh_PLANSSOC:
                    value = self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLAN][JSONKEY_PLAN_SOC]
                    return str(int(value))  # float(int(value))/100
                elif is_veh_PLANSTIME:
                    return self._convert_time(self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLAN][JSONKEY_PLAN_TIME])

            elif JSONKEY_PLANS_DEPRECATED in self.data[JSONKEY_VEHICLES][vehicle_id] and len(self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLANS_DEPRECATED]) > 0:
                if is_veh_PLANSSOC:
                    value = self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLANS_DEPRECATED][0][JSONKEY_PLAN_SOC]
                    return str(int(value))  # float(int(value))/100
                elif is_veh_PLANSTIME:
                    return self._convert_time(self.data[JSONKEY_VEHICLES][vehicle_id][JSONKEY_PLANS_DEPRECATED][0][JSONKEY_PLAN_TIME])

            else:
                return None
        else:
            if tag.json_key in self.data[JSONKEY_VEHICLES][vehicle_id]:
                return self.data[JSONKEY_VEHICLES][vehicle_id][tag.json_key]
            elif tag.json_key_alias is not None and tag.json_key_alias in self.data[JSONKEY_VEHICLES][vehicle_id]:
                return self.data[JSONKEY_VEHICLES][vehicle_id][tag.json_key_alias]
            else:
                return "0"

    async def async_write_plan(self, vehicle_name:str, loadpoint_idx: str, soc_or_energy: str, rfc_date: str, precondition: int | None = None):
        if vehicle_name is not None and loadpoint_idx is None:
            return await self.bridge.write_vehicle_plan(vehicle_id=vehicle_name, soc=soc_or_energy, rfc_date=rfc_date, precondition=precondition)
        else:
            return await self.bridge.write_loadpoint_plan(idx=loadpoint_idx, energy=soc_or_energy, rfc_date=rfc_date)

    async def async_delete_plan(self, vehicle_name:str, loadpoint_idx: str):
        if vehicle_name is not None and loadpoint_idx is None:
            return await self.bridge.write_vehicle_plan(vehicle_id=vehicle_name, soc=None, rfc_date=None, precondition=-1)
        else:
            return await self.bridge.write_loadpoint_plan(idx=loadpoint_idx, energy=None, rfc_date=None)

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

        if tag.json_key not in result or result[tag.json_key] is None:
            _LOGGER.info(f"could not write value: '{value}' to: {tag} result was: {result}")
        else:
            # IMH0 it's quite tricky to patch the self.data object here... but we try!
            if tag.type == EP_TYPE.SITE:
                if tag.json_key in self.data:
                    self.data[tag.json_key] = value

            elif tag.type == EP_TYPE.LOADPOINTS:
                if idx_str is not None:
                    idx = int(idx_str)
                    if len(self.data[JSONKEY_LOADPOINTS]) > idx - 1:
                        if tag.json_key in self.data[JSONKEY_LOADPOINTS][idx - 1]:
                            self.data[JSONKEY_LOADPOINTS][idx - 1][tag.json_key] = value

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

    def device_info_dict_for_loadpoint(self, addon: str) -> dict:
        # check also 'read_evcc_config_on_startup' where we create the default device_info_dict
        unique_device_id = slugify(f"did_{self._config_entry.data.get(CONF_HOST)}_{addon}")
        a_device_info_dict = {
            "identifiers": {(DOMAIN, unique_device_id)},
            "manufacturer": MANUFACTURER,
            "name": f"{NAME_SHORT} - {self.lang_map["device_name_loadpoint"]} {addon} [{self._system_id}]",
            "sw_version": self._version
        }
        return a_device_info_dict

    def device_info_dict_for_vehicle(self, addon: str) -> dict:
        # check also 'read_evcc_config_on_startup' where we create the default device_info_dict
        unique_device_id = slugify(f"did_{self._config_entry.data.get(CONF_HOST)}_{addon}")
        a_device_info_dict = {
            "identifiers": {(DOMAIN, unique_device_id)},
            "manufacturer": MANUFACTURER,
            "name": f"{NAME_SHORT} - {self.lang_map["device_name_vehicle"]} {addon} [{self._system_id}]",
            "sw_version": self._version
        }
        return a_device_info_dict

    @property
    def grid_data_as_object(self) -> bool:
        return self._grid_data_as_object

    @property
    def battery_data_as_object(self) -> bool:
        return self._battery_data_as_object

class EvccBaseEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name_addon = None

    def __init__(self, entity_type:str, coordinator: EvccDataUpdateCoordinator, description: EntityDescription) -> None:
        if hasattr(description, "tag"):
            self.tag = description.tag
        else:
            self.tag = None

        self.lp_idx = None
        if hasattr(description, "lp_idx"):
            self.lp_idx = description.lp_idx
        else:
            self.lp_idx = None

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
                description = replace(
                    description,
                    native_unit_of_measurement = description.native_unit_of_measurement.replace("@@@", coordinator.currency)
                )

        self.entity_description = description
        self.coordinator = coordinator
        self.entity_id = f"{entity_type}.{self.coordinator.system_id}_{camel_to_snake(description.key)}".lower()

    def _name_internal(self, device_class_name: str | None, platform_translations: dict[str, Any]) -> str | UndefinedType | None:
        tmp = super()._name_internal(device_class_name, platform_translations)
        if tmp is not None and "@@@" in tmp:
            tmp = tmp.replace("@@@", self.coordinator.currency)
        if self._attr_name_addon is not None:
            return f"{self._attr_name_addon} {tmp}"
        else:
            return tmp

    @property
    def device_info(self) -> dict:
        if self.tag.type == EP_TYPE.SESSIONS and self.tag.subtype is not None and self._attr_name_addon is not None:
            if self.tag.subtype == SESSIONS_KEY_LOADPOINTS:
                return self.coordinator.device_info_dict_for_loadpoint(self._attr_name_addon)
            elif self.tag.subtype == SESSIONS_KEY_VEHICLES:
                return self.coordinator.device_info_dict_for_vehicle(self._attr_name_addon)

        if self.tag.type is not EP_TYPE.CIRCUITS and self._attr_name_addon is not None:
            return self.coordinator.device_info_dict_for_loadpoint(self._attr_name_addon)
        else:
            return self.coordinator.device_info_dict

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{DOMAIN}.{self.entity_id.split('.')[1]}"

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
