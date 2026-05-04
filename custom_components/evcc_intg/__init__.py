import asyncio
import logging
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

import aiohttp
from aiohttp import ClientConnectionError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, EVENT_HOMEASSISTANT_STARTED, CONF_PASSWORD
from homeassistant.core import HomeAssistant, Event, SupportsResponse, CoreState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry, config_validation as config_val, device_registry as device_reg
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.helpers.typing import UNDEFINED, UndefinedType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify
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
    JSONKEY_STAT_CHARGED_KWH,
    JSONKEY_STAT_SOLAR_PERCENTAGE,
    JSONKEY_STAT_SOLAR_KWH_TEMPLATE,
    ADDITIONAL_ENDPOINTS_DATA_TARIFF,
    ADDITIONAL_ENDPOINTS_DATA_SESSIONS,
    SESSIONS_KEY_LOADPOINTS,
    SESSIONS_KEY_VEHICLES,
    ADDITIONAL_ENDPOINTS_DATA_EVCCCONF,
    EVCCCONF_DEVICE_TYPES,
    EVCCCONF_KEY_CONFIG,
    EVCCCONF_KEY_DATA,
    JSONKEY_CIRCUITS,
    EP_TYPE
)
from custom_components.evcc_intg.pyevcc_ha.keys import Tag, camel_to_snake
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
from .entity import CustomFriendlyNameEntity
from .service import EvccService

_LOGGER: logging.Logger = logging.getLogger(__package__)

WEBSOCKET_WATCHDOG_INTERVAL: Final = timedelta(minutes=5, seconds=1)
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

    # yes - hurray! we can now clean up the device registry...
    purge_all_devices = config_entry.data.get(CONF_PURGE_ALL, False)
    asyncio.create_task(check_device_registry(hass, purge_all_devices, config_entry.entry_id))
    if purge_all_devices:
        # we remove the 'purge_all_devices' flag from the config entry...
        new_data_dict = config_entry.data.copy()
        del new_data_dict[CONF_PURGE_ALL]
        hass.config_entries.async_update_entry(config_entry, data=new_data_dict, options={}, version=CONFIG_VERSION, minor_version=CONFIG_MINOR_VERSION)
        _LOGGER.debug(f"async_setup_entry(): Updated configuration (PURGE_ALL removed): {new_data_dict}")

    # loading a possible existing cookie file (from the .storage so we don't have the need
    # to login to the evcc backend with every startup
    cookie_path = str(Path(hass.config.config_dir).joinpath(STORAGE_DIR, f"cookies_evcc_intg_{config_entry.entry_id}.txt"))

    # ensure that our storage directory exists...
    def prepare_dir():
        os.makedirs(os.path.dirname(cookie_path), exist_ok=True)
    await hass.async_add_executor_job(prepare_dir)

    the_persistent_cookie_jar = aiohttp.CookieJar(unsafe=True)
    if os.path.exists(cookie_path):
        if config_entry.data.get(CONF_PASSWORD):
            try:
                await hass.async_add_executor_job(the_persistent_cookie_jar.load, cookie_path)
                _LOGGER.debug(f"async_setup_entry(): Loaded cookies from file: '{cookie_path}'")
            except Exception as err:
                _LOGGER.info(f"async_setup_entry(): Could not load cookies from {cookie_path}: {type(err).__name__} - {err}")
        else:
            # when there is no password BUT the cookie file still exist... we should delete it!
            def delete_cookie_file():
                os.remove(cookie_path)
            await hass.async_add_executor_job(delete_cookie_file)


    # using the same http client for test and final integration...
    http_session = async_create_clientsession(hass, verify_ssl=False, cookie_jar=the_persistent_cookie_jar)

    # simple check, IF the evcc server is up and running ... raise an 'ConfigEntryNotReady' if
    # the configured backend could not be reached - then let HA deal with an optional retry
    await check_evcc_is_available(http_session, config_entry)

    # ok - when the evcc-server is available we can continue with the init process...
    coordinator = EvccDataUpdateCoordinator(hass, http_session, config_entry, cookie_path)
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady
    else:
        # now we can attempt to initialize our coordinator with the data already read...
        if not await coordinator.read_evcc_config_on_startup(hass):
            _LOGGER.warning(f"async_setup_entry(): coordinator.read_evcc_config_on_startup() was not completed successfully - please enable debug-log option in order to find a posiible root cause.")

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

        # If Home Assistant is already in a running state, start the watchdog
        # immediately, else trigger it after Home Assistant has finished starting.
        if coordinator.use_ws:
            if hass.state is CoreState.running:
                _LOGGER.debug(f"async_setup_entry(): starting watchdog INSTANTLY")
                await coordinator.start_watchdog()
            else:
                _LOGGER.debug(f"async_setup_entry(): starting watchdog delayed... (when EVENT_HOMEASSISTANT_STARTED is fired)")
                hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, coordinator.start_watchdog)

        config_entry.async_on_unload(config_entry.add_update_listener(entry_update_listener))

        # async def delayed_startup_logic(hass):
        #     _LOGGER.debug(f"delayed_startup_logic(): STARTING delayed_startup_logic... [will wait another 30sec...]")
        #     await asyncio.sleep(30)
        #     _LOGGER.debug(f"delayed_startup_logic(): finally trigger an integration RELOAD!")
        #     await hass.config_entries.async_reload(config_entry.entry_id)
        #
        # async_at_start(hass, delayed_startup_logic)

        # ok we are done...
        _LOGGER.debug(f"async_setup_entry(): completed successfully for entry: {config_entry.entry_id}")
        return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    _LOGGER.debug(f"async_unload_entry(): called for entry: {config_entry.entry_id}")
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


async def async_remove_config_entry_device(hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry) -> bool:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    # Only handle devices belonging to this integration/config entry
    if config_entry.entry_id not in device_entry.config_entries:
        return False

    if not any(identifier[0] == DOMAIN for identifier in device_entry.identifiers):
        return False

    # Do not allow removing the main evcc device manually.
    main_device_id = slugify(f"did_{config_entry.data.get(CONF_HOST)}")
    if (DOMAIN, main_device_id) in device_entry.identifiers:
        return False

    # Allow removing dynamic child devices like vehicles/loadpoints.
    return coordinator is not None


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
        _LOGGER.debug(f"check_device_registry(): check device registry for outdated {DOMAIN} devices...")
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
                                    _LOGGER.info(f"check_device_registry(): found a OLD {DOMAIN} DeviceEntry: {a_device_entry}")
                                    devices_to_delete.append(a_device_entry.id)

                            #elif intg_version != "UNKNOWN":
                            #    if not f"{ident_value}".__contains__(intg_version):
                            #        devices_to_delete.append(a_device_entry.id)

                if len(devices_to_delete) > 0:
                    devices_to_delete = list(dict.fromkeys(devices_to_delete))
                    if purge_all:
                        _LOGGER.info(f"check_device_registry(): CLEAN ALL {DOMAIN} DeviceEntries: {devices_to_delete}")
                    else:
                        _LOGGER.info(f"check_device_registry(): NEED TO DELETE old {DOMAIN} DeviceEntries: {devices_to_delete}")

                    for a_device_entry_id in devices_to_delete:
                        a_device_reg.async_remove_device(device_id=a_device_entry_id)

        DEVICE_REG_CLEANUP_RUNNING = False


class EvccDataUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, http_session: aiohttp.ClientSession, config_entry, cookie_path: str):
        # make sure we to not log the admin_pwd on console...
        log_dict = config_entry.data.copy()
        if CONF_PASSWORD in log_dict:
            log_dict[CONF_PASSWORD] = "********"
        _LOGGER.debug(f"starting evcc_intg for: data:{log_dict}")

        self.name = config_entry.title
        self.use_ws = config_entry.data.get(CONF_USE_WS, True)

        lang = hass.config.language.lower()
        if lang in TRANSLATIONS:
            self.lang_map = TRANSLATIONS[lang]
        else:
            self.lang_map = TRANSLATIONS["en"]

        # we need to set the 'config_update_interval_in_seconds' before we init the bridge, cause we need
        # the interval from the coordinator in the bridge (for the config updates)...
        self.update_interval_in_seconds_from_config_entry = config_entry.data.get(CONF_SCAN_INTERVAL, 30)

        self.bridge = EvccApiBridge(host=config_entry.data.get(CONF_HOST, "NOT-CONFIGURED"),
                                    web_session=http_session,
                                    coordinator=self,
                                    lang=lang,
                                    opt_password=config_entry.data.get(CONF_PASSWORD, None))


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
        self._device_info_show_ws_state = False
        self._circuit = {}
        self._loadpoint = {}
        self._vehicle = {}

        # actually the _config_entities data should contain the 'same'
        # as the '_circuit', '_loadpoint' and '_vehicle' data, but it's
        # all used in the api/config section that requires admin password.
        # so for now we keep this config data separate from our core
        # configuration entries
        self._config_entities = {}

        self._version = None
        self._grid_data_as_object = False
        self._battery_data_as_object = False
        self._watchdog = None
        self._ws_start_task = None

        # a global store for entities that we must manipulate later on...
        self.select_entities_dict = {}

        # just for internal usage...
        self._http_session = http_session
        self._cookie_path_on_fs = cookie_path

        # when we use the websocket we need to call the super constructor without update_interval...
        if self.use_ws:
            super().__init__(hass, _LOGGER, name=DOMAIN)
        else:
            super().__init__(hass, _LOGGER, name=DOMAIN,
                             update_interval=timedelta(seconds=self.update_interval_in_seconds_from_config_entry))

    # Callable[[Event], Any]
    def __call__(self, evt: Event) -> bool:
        _LOGGER.debug(f"Event arrived: {evt}")
        return True

    async def call_later_update_device_registry(self, now:Any):
        _LOGGER.debug(f"call_later_update_device_registry(): called with '{now}'")
        if self._device_info_show_ws_state:
            if self.hass is not None:
                a_device_reg = device_reg.async_get(self.hass)
                if a_device_reg is not None:
                    device = a_device_reg.async_get_device(identifiers=self._device_info_dict["identifiers"])
                    if device:
                        _LOGGER.info(f"call_later_update_device_registry(): device registry update triggered for device {device.name}")
                        if self.bridge.ws_connected and self.bridge.ws_check_last_update():
                            f_model = f"{self.lang_map.get("ws_connected", "WebSocket connected:")} ✅"
                        else:
                            f_model = f"{self.lang_map.get("ws_connected", "WebSocket connected:")} ⛔"

                        a_device_reg.async_update_device(
                            device.id,
                            model=f_model
                        )

    async def save_cookies(self):
        """Save cookies to file."""
        if self._cookie_path_on_fs is None:
            _LOGGER.info(f"save_cookies(): Failed to save cookies to fs - no 'self._cookie_path_on_fs' is set")
            return
        try:
            await self.hass.async_add_executor_job(self._http_session.cookie_jar.save, self._cookie_path_on_fs)
            _LOGGER.debug(f"save_cookies(): Saved cookies to file: '{self._cookie_path_on_fs}'")
        except Exception as err:
            _LOGGER.info(f"save_cookies(): Failed to save cookies to {self.cookie_path}: {type(err).__name__} - {err}")

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
            async_call_later(self.hass, 5, self.call_later_update_device_registry)

    def _check_for_ws_task_and_cancel_if_running(self):
        if self._ws_start_task is not None and not self._ws_start_task.done():
            _LOGGER.debug(f"Watchdog: websocket connect task is still running - canceling it...")
            try:
                canceled = self._ws_start_task.cancel()
                _LOGGER.debug(f"Watchdog: websocket connect task was CANCELED? {canceled}")
            except BaseException as ex:
                _LOGGER.info(f"Watchdog: websocket connect task cancel failed: {type(ex).__name__} - {ex}")
            self._ws_start_task = None

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
                self._check_for_ws_task_and_cancel_if_running()
                self._ws_start_task = self._config_entry.async_create_background_task(self.hass, self.bridge.connect_ws(), "ws_connection")
                if self._ws_start_task is not None:
                    _LOGGER.debug(f"Watchdog: task created {self._ws_start_task.get_coro()}")
                    async_call_later(self.hass, 10, self.call_later_update_device_registry)
            else:
                _LOGGER.debug(f"Watchdog: websocket is connected")
                if not self.bridge.ws_check_last_update():
                    self._check_for_ws_task_and_cancel_if_running()
                    async_call_later(self.hass, 5, self.call_later_update_device_registry)
                else:
                    pass
                    # move any time related checks directly into the websocket handler... (so we check with
                    # every new data arrival, of some additional senso data should be requested)...

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
        # Please note that the identifiers object must be a (...)
        # for the 'unique_device_id' we will use the initial specified HOST/IP (if it is later overwritten with
        # a changed host, we're going still use the initial one)
        unique_device_id = slugify(f"did_{self._config_entry.data.get(CONF_HOST)}")
        self._device_info_dict = {
            "identifiers": {(DOMAIN, unique_device_id)},
            "manufacturer": MANUFACTURER,
            "name": f"{NAME} [{self._system_id}]",
            "sw_version": self._version,
            "model": None
        }

        # IF we have a evcc-admin password in our configuration, we can also take the config from the
        # bridge to the coordinator... [not so sure what we will do, when this configuration will not
        # match our "default" loadpoint & vehicle config... ?!]
        if self._config_entry.data.get(CONF_PASSWORD):
            self._config_entities = initdata.get(ADDITIONAL_ENDPOINTS_DATA_EVCCCONF, {}).get(EVCCCONF_KEY_CONFIG, {})
            if len(self._config_entities) == 0:
                _LOGGER.debug(f"read_evcc_config_on_startup(): no configuration entities found")

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

        _LOGGER.debug(f"read_evcc_config_on_startup(): Use Websocket: {self.use_ws} (already started? {self.bridge.ws_connected}) LPs: {len(self._loadpoint)}, VEHs: {len(self._vehicle)}, CONFs: {len(self._config_entities)}, CT: '{self._cost_type}', CUR: '{self._currency}', GridAsObject: {self._grid_data_as_object}, BatteryAsObject: {self._battery_data_as_object}")
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

    def read_tag(self, a_tag: Tag, idx: int = None):
        ret = None
        if self.data is not None:
            if a_tag.type == EP_TYPE.LOADPOINTS:
                ret = self.read_tag_loadpoint(a_tag=a_tag, loadpoint_idx=idx)
                # quick hack for subtype support
                if isinstance(ret, dict) and a_tag.subtype is not None:
                    ret = ret.get(a_tag.subtype, ret)

            elif a_tag.type == EP_TYPE.VEHICLES:
                ret = self.read_tag_vehicle_int(a_tag=a_tag, loadpoint_idx=idx)
                # quick hack for subtype support
                if isinstance(ret, dict) and a_tag.subtype is not None:
                    ret = ret.get(a_tag.subtype, ret)

            # in the case of circuits, the 'idx' is not a int - it is a str and this
            # str is the key in the circuits dict...
            elif a_tag.type == EP_TYPE.CIRCUITS and idx is not None:
                circuit_data = self.data.get(JSONKEY_CIRCUITS, {}).get(idx, {})
                ret = circuit_data.get(a_tag.json_key, None) if a_tag.json_key in circuit_data else None

            elif a_tag.type == EP_TYPE.SITE:
                # this must be done generally... not only for the SITE tag...
                if a_tag.json_key in self.data:
                    ret = self.data[a_tag.json_key]

                elif a_tag.json_key_alias is not None and a_tag.json_key_alias in self.data:
                    ret = self.data[a_tag.json_key_alias]

                elif a_tag.subtype is not None and a_tag.subtype in self.data:
                    a_obj = self.data[a_tag.subtype]
                    if isinstance(a_obj, dict) and len(a_obj) > 0:
                        if a_tag.json_key in a_obj:
                            ret = a_obj[a_tag.json_key]
                        elif a_tag.json_key_alias is not None and a_tag.json_key_alias in a_obj:
                            ret = a_obj[a_tag.json_key_alias]

            elif a_tag.type == EP_TYPE.EVOPT:
                ret = self.data.get(EP_TYPE.EVOPT.value, {}).get(a_tag.json_key, None)

            elif a_tag.type == EP_TYPE.STATISTICS:
                ret = self.read_tag_statistics(a_tag=a_tag)

            elif a_tag.type == EP_TYPE.TARIFF:
                ret = self.read_tag_tariff(a_tag=a_tag)

            elif a_tag.type == EP_TYPE.EVCCCONF:
                ret = self.read_tag_configuration(a_tag=a_tag, config_device_identifier=None)

        # _LOGGER.debug(f"read from {tag.key} [@idx {idx}] -> {ret}")
        return ret

    def read_tag_configuration(self, a_tag: Tag, config_device_identifier: str):
        if config_device_identifier is None:
            return None

        device_data = self.data.get(ADDITIONAL_ENDPOINTS_DATA_EVCCCONF, {}).get(EVCCCONF_KEY_DATA, {})
        if len(device_data) == 0:
            return None

        return device_data.get(a_tag.subtype, {}).get(config_device_identifier.lower(), {}).get(a_tag.json_key, {}).get("value")

    def read_tag_tariff(self, a_tag: Tag):
        if ADDITIONAL_ENDPOINTS_DATA_TARIFF in self.data:
            if a_tag.json_key in self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF]:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF][a_tag.json_key]
            elif a_tag.json_key_alias is not None and a_tag.json_key_alias in self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF]:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_TARIFF][a_tag.json_key_alias]

    def read_tag_sessions(self, a_tag: Tag, additional_key: str = None):
        if ADDITIONAL_ENDPOINTS_DATA_SESSIONS in self.data:
            if a_tag == Tag.CHARGING_SESSIONS:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS]
            elif a_tag == Tag.CHARGING_SESSIONS_VEHICLES:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_VEHICLES]
            elif a_tag == Tag.CHARGING_SESSIONS_LOADPOINTS:
                return self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_LOADPOINTS]

            elif a_tag.subtype is not None and a_tag.subtype in self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS]:
                # vehicles or loadpoints sub-tag ?
                a_dict = self.data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][a_tag.subtype]
                if additional_key is not None and additional_key in a_dict:
                    return a_dict[additional_key].get(a_tag.json_key, None)
                else:
                    return a_dict.get(a_tag.json_key, None)

    def read_tag_statistics(self, a_tag: Tag):
        if JSONKEY_STATISTICS in self.data:
            if a_tag.subtype in self.data[JSONKEY_STATISTICS]:
                period_data = self.data[JSONKEY_STATISTICS][a_tag.subtype]
                if a_tag.json_key == JSONKEY_STAT_SOLAR_KWH_TEMPLATE:
                    charged = period_data.get(JSONKEY_STAT_CHARGED_KWH, 0) or 0
                    solar_pct = period_data.get(JSONKEY_STAT_SOLAR_PERCENTAGE, 0) or 0
                    return round(float(charged) * float(solar_pct) / 100.0, 4)
                if a_tag.json_key in period_data:
                    return period_data[a_tag.json_key]
                elif a_tag.json_key_alias is not None and a_tag.json_key_alias in period_data:
                    return period_data[a_tag.json_key_alias]

    def read_tag_loadpoint(self, a_tag: Tag, loadpoint_idx: int = None):
        if loadpoint_idx is not None and len(self.data[JSONKEY_LOADPOINTS]) > loadpoint_idx - 1:
            # if tag == Tag.CHARGECURRENTS:
            #    _LOGGER.error(f"valA? {self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]}")
            #    _LOGGER.error(f"valB? {self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][tag.key]}")

            value = None
            if a_tag.json_key in self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]:
                value = self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][a_tag.json_key]
            elif a_tag.json_key_alias is not None and a_tag.json_key_alias in self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]:
                value = self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][a_tag.json_key_alias]

            if value is not None:
                if a_tag == Tag.PLANTIME or a_tag == Tag.EFFECTIVEPLANTIME:
                    value = self._convert_time(value)

                elif a_tag == Tag.PLANPROJECTEDSTART or a_tag == Tag.PLANPROJECTEDEND:
                    # the API already return a ISO 8601 'date' here - but we need to convert it to a datetime object
                    # so that it then can be finally converted by the default Sensor to a ISO 8601 date...
                    value = self._convert_time(value)

                elif a_tag == Tag.PVREMAINING:
                    # the API just return seconds here - but we need to convert it to a datetime object so actually
                    # the value is 'now' + seconds...
                    if value != 0:
                        value = datetime.now(timezone.utc) + timedelta(seconds=value)
                    else:
                        value = None

                return value

    def read_tag_vehicle_int(self, a_tag: Tag, loadpoint_idx: int = None):
        if len(self.data) > 0 and JSONKEY_LOADPOINTS in self.data and loadpoint_idx is not None:
            try:
                if len(self.data[JSONKEY_LOADPOINTS]) > loadpoint_idx - 1:
                    if Tag.LP_VEHICLENAME.json_key in self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1]:
                        vehicle_id = self.data[JSONKEY_LOADPOINTS][loadpoint_idx - 1][Tag.LP_VEHICLENAME.json_key]
                        if vehicle_id is not None:
                            if len(vehicle_id) > 0:
                                return self.read_tag_vehicle_str(a_tag=a_tag, vehicle_id=vehicle_id)
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

    def read_tag_vehicle_str(self, a_tag: Tag, vehicle_id: str):
        is_veh_PLANSSOC = a_tag == Tag.VEHICLEPLANSOC
        is_veh_PLANSTIME = a_tag == Tag.VEHICLEPLANTIME
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
            if a_tag.json_key in self.data[JSONKEY_VEHICLES][vehicle_id]:
                return self.data[JSONKEY_VEHICLES][vehicle_id][a_tag.json_key]
            elif a_tag.json_key_alias is not None and a_tag.json_key_alias in self.data[JSONKEY_VEHICLES][vehicle_id]:
                return self.data[JSONKEY_VEHICLES][vehicle_id][a_tag.json_key_alias]
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

    async def async_press_tag(self, a_tag: Tag, value, idx: str = None, entity: Entity = None) -> dict:
        result = await self.bridge.press_tag(a_tag, value, idx)
        _LOGGER.debug(f"async_press_tag(): press result: {result}")

        if a_tag == Tag.EVCC_SHUTDOWN:
            if result.get(a_tag.json_key, False):
                _LOGGER.info(f"async_press_tag(): EVCC shutdown initiated successfully... we need to reschedule a reconnect!")
                self.stop_watchdog()
                self.bridge.clear_data(clear_evcc_data=False)
                async_call_later(self.hass, 15, self.start_watchdog)
            else:
                _LOGGER.info(f"async_press_tag(): EVCC shutdown failed with result: {result}")
        else:
            if entity is not None and not self.bridge.ws_connected:
                entity.async_schedule_update_ha_state(force_refresh=True)

        return result

    async def async_write_tag(self, a_tag: Tag, value, idx_str: str = None, entity: Entity = None) -> dict:
        """Update single data"""
        result = await self.bridge.write_tag(a_tag, value, idx_str)
        _LOGGER.debug(f"write result: {result}")

        if a_tag.json_key not in result or result[a_tag.json_key] is None:
            _LOGGER.info(f"could not write value: '{value}' to: {a_tag} result was: {result}")
        else:
            # IMH0 it's quite tricky to patch the self.data object here... but we try!
            if a_tag.type == EP_TYPE.SITE:
                if a_tag.json_key in self.data:
                    self.data[a_tag.json_key] = value

            elif a_tag.type == EP_TYPE.LOADPOINTS:
                if idx_str is not None:
                    idx = int(idx_str)
                    if len(self.data[JSONKEY_LOADPOINTS]) > idx - 1:
                        if a_tag.json_key in self.data[JSONKEY_LOADPOINTS][idx - 1]:
                            self.data[JSONKEY_LOADPOINTS][idx - 1][a_tag.json_key] = value

            elif a_tag.type == EP_TYPE.VEHICLES:
                # TODO ?!
                _LOGGER.debug(f"{a_tag} no data update!")
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

    def device_info_dict_for_circuit(self, addon: str) -> dict:
        # check also 'read_evcc_config_on_startup' where we create the default device_info_dict
        unique_device_id = slugify(f"did_{self._config_entry.data.get(CONF_HOST)}_{addon}")
        a_device_info_dict = {
            "identifiers": {(DOMAIN, unique_device_id)},
            "manufacturer": MANUFACTURER,
            "name": f"{NAME_SHORT} - {self.lang_map["device_name_circuit"]} {addon} [{self._system_id}]",
            "sw_version": self._version
        }
        return a_device_info_dict

    def device_info_dict_for_meter(self, addon: str) -> dict:
        # check also 'read_evcc_config_on_startup' where we create the default device_info_dict
        unique_device_id = slugify(f"did_{self._config_entry.data.get(CONF_HOST)}_{addon}")
        device_name_meter = "device_name_meter"
        if self.data is not None:
            meter_data = self.data.get(ADDITIONAL_ENDPOINTS_DATA_EVCCCONF, {}).get(EVCCCONF_KEY_CONFIG, {}).get(EVCCCONF_DEVICE_TYPES.METER.value, {})
            if addon in meter_data:
                device_name_meter = f"device_name_meter_{meter_data[addon].lower()}"
        a_device_info_dict = {
            "identifiers": {(DOMAIN, unique_device_id)},
            "manufacturer": MANUFACTURER,
            "name": f"{NAME_SHORT} - {self.lang_map[device_name_meter]} {addon} [{self._system_id}]",
            "sw_version": self._version
        }
        return a_device_info_dict

    @property
    def grid_data_as_object(self) -> bool:
        return self._grid_data_as_object

    @property
    def battery_data_as_object(self) -> bool:
        return self._battery_data_as_object

class EvccBaseEntity(CustomFriendlyNameEntity):
    _attr_has_entity_name = True
    _attr_name_addon = None

    def __init__(self, entity_type:str, coordinator: EvccDataUpdateCoordinator, description: EntityDescription) -> None:
        super().__init__(coordinator, description)
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
        if self._attr_name_addon is not None:
            if self.tag.type == EP_TYPE.EVCCCONF:
                if self.tag.subtype == EVCCCONF_DEVICE_TYPES.VEHICLE.value:
                    return self.coordinator.device_info_dict_for_vehicle(self._attr_name_addon)
                # elif self.tag.subtype == EVCCCONF_DEVICE_TYPES.CIRCUIT.value:
                #     return self.coordinator.device_info_dict_for_circuit(self._attr_name_addon)
                elif self.tag.subtype == EVCCCONF_DEVICE_TYPES.METER.value:
                    return self.coordinator.device_info_dict_for_meter(self._attr_name_addon)

            # if self.tag.type is EP_TYPE.CIRCUITS:
            #     return self.coordinator.device_info_dict_for_circuit(self._attr_name_addon)

            if self.tag.type == EP_TYPE.SESSIONS and self.tag.subtype is not None:
                if self.tag.subtype == SESSIONS_KEY_LOADPOINTS:
                    return self.coordinator.device_info_dict_for_loadpoint(self._attr_name_addon)

                elif self.tag.subtype == SESSIONS_KEY_VEHICLES:
                    return self.coordinator.device_info_dict_for_vehicle(self._attr_name_addon)

            # all other sensors with a _attr_name_addon (except CIRCUITS) must be loadpoint data...
            if self.tag.type is not EP_TYPE.CIRCUITS:
                return self.coordinator.device_info_dict_for_loadpoint(self._attr_name_addon)

        # only the main/site device information should show the connection status of a
        # possible existing websocket connection
        self.coordinator._device_info_show_ws_state = self.coordinator.use_ws
        return self.coordinator.device_info_dict

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{DOMAIN}.{self.entity_id.split('.')[1]}".lower()

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
        await super().async_added_to_hass()

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

        # check if there is a user specified entity name (overwritten)
        if registry_entry := self.registry_entry:
            if registry_entry.has_entity_name and registry_entry.name is not None:
                name = registry_entry.name

        # we overwrite the default impl here and just return our 'name'
        # return f"{device_name} {name}" if device_name else name
        if device_entry.name_by_user is not None:
            return f"{device_entry.name_by_user} {name}" if device_name else name
        elif self.coordinator.include_evcc_prefix:
            return f"[evcc] {name}"
        else:
            return name
