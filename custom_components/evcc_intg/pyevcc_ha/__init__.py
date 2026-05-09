import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from json import JSONDecodeError
from numbers import Number
from time import time
from typing import Callable, Final

import aiohttp
from aiohttp import ClientResponseError, ClientConnectionError, ClientError, ClientTimeout
from dateutil import parser
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from custom_components.evcc_intg.pyevcc_ha.const import (
    TRANSLATIONS,
    JSONKEY_LOADPOINTS,
    JSONKEY_VEHICLES,
    ADDITIONAL_ENDPOINTS_DATA_TARIFF,
    ADDITIONAL_ENDPOINTS_DATA_SESSIONS,
    SESSIONS_KEY_RAW,
    SESSIONS_KEY_TOTAL,
    SESSIONS_KEY_VEHICLES,
    SESSIONS_KEY_LOADPOINTS,
    ADDITIONAL_ENDPOINTS_DATA_EVCCCONF,
    EVCCCONF_KEY_CONFIG,
    EVCCCONF_KEY_DATA,
    EVCCCONF_OBJECT_HIERARCHY,
    EVCCCONF_DEVICES,
    EVCCCONF_DEVICE_TYPES,
    EVCCCONF_SITE,
    EVCCCONF_LOADPOINTS,
    EP_TYPE,
)
from custom_components.evcc_intg.pyevcc_ha.keys import Tag, IS_TRIGGER

_LOGGER: logging.Logger = logging.getLogger(__package__)

static_5sec_timeout: Final = ClientTimeout(total=5)
static_30sec_timeout: Final = ClientTimeout(total=30)
RAW_CLIENT_RESPONSE_KEY = "aiohttp.ClientResponse"

async def _do_request(method: Callable, return_raw_client_response:bool=False) -> dict:
    try:
        async with method as res:
            try:
                if 199 < res.status < 300:
                    try:
                        if "application/json" in res.content_type.lower():
                            try:
                                data = await res.json()
                                if data is None:
                                    if return_raw_client_response:
                                        return {RAW_CLIENT_RESPONSE_KEY: res}
                                    else:
                                        return {}

                                elif isinstance(data, dict):
                                    # check if the data is a dict with a single key "result" - this 'result' container
                                    # will be removed in the future [https://github.com/evcc-io/evcc/pull/22299]
                                    if "result" in data and len(data) == 1:
                                        data = data["result"]
                                    return data

                                elif isinstance(data, list):
                                    return data

                                elif len(str(data).strip()) == 0:
                                    if return_raw_client_response:
                                        return {RAW_CLIENT_RESPONSE_KEY: res}
                                    else:
                                        return {}

                                else:
                                    # it's a single plain value (number, string, bool)
                                    return data

                            except JSONDecodeError as json_exc:
                                _LOGGER.warning(f"APP-API: JSONDecodeError while 'await res.json(): {json_exc} [caused by {res.request_info.method} {res.request_info.url}]")
                        else:
                            # if this is no JSON response, we just return the raw response...
                            if return_raw_client_response:
                                return {RAW_CLIENT_RESPONSE_KEY: res}
                            else:
                                return {}

                    except ClientResponseError as io_exc:
                        _LOGGER.warning(f"APP-API: ClientResponseError while 'await res.json(): {io_exc} [caused by {res.request_info.method} {res.request_info.url}]")

                elif int(res.headers["Content-Length"]) > 0:
                    try:
                        content = await res.text()
                        _LOGGER.warning(f"_do_request() - 'res.status == {res.status} content: {content} [caused by {res.request_info.method} {res.request_info.url}]")

                    except ClientResponseError as io_exc:
                        _LOGGER.warning(f"_do_request() ClientResponseError while 'res.status == {res.status} res.json(): {io_exc} [caused by {res.request_info.method} {res.request_info.url}]")

                else:
                    _LOGGER.warning(f"_do_request() failed with http-status {res.status} [caused by {res.request_info.method} {res.request_info.url}]")

            except ClientError as io_exc:
                _LOGGER.warning(f"_do_request() failed cause: {io_exc} [caused by {res.request_info.method} {res.request_info.url}]")
            except Exception as ex:
                _LOGGER.warning(f"_do_request() failed cause: {type(ex).__name__} - {ex} [caused by {res.request_info.method} {res.request_info.url}]")
            return {}

    except ClientError as exception:
        _LOGGER.warning(f"_do_request() cause of ClientConnectorError: {exception}")
    except Exception as other:
        _LOGGER.warning(f"_do_request() unexpected: {type(other).__name__} - {other}")


@staticmethod
def calculate_session_sums(sessions_resp, json_resp: dict):
    vehicle_sums = {}
    loadpoint_sums = {}

    for a_session_entry in sessions_resp:
        try:
            a_vehicle = a_session_entry.get("vehicle", "")
            a_loadpoint = a_session_entry.get("loadpoint", "")
            no_veh_data_avail = a_vehicle is None or len(a_vehicle) == 0
            no_lp_data_avail = a_loadpoint is None or len(a_loadpoint) == 0
            if no_veh_data_avail and no_lp_data_avail:
                _LOGGER.info(f"calculate_session_sums(): missing ANY-keyinfo in session entry: {a_session_entry}")
            elif no_veh_data_avail:
                _LOGGER.debug(f"calculate_session_sums(): missing 'vehicle' info in session entry: {a_session_entry}")
            elif no_lp_data_avail:
                _LOGGER.debug(f"calculate_session_sums(): missing 'loadpoint' info in session entry: {a_session_entry}")

            charge_duration_in_nano_seconds = a_session_entry.get("chargeDuration", 0)
            if (charge_duration_in_nano_seconds is None or
                    not isinstance(charge_duration_in_nano_seconds, Number) or
                    charge_duration_in_nano_seconds < 0):
                charge_duration = _get_charge_duration_from_create_finish(a_session_entry)
                if charge_duration is None:
                    charge_duration = 0
            else:
                # we need to convert nanoseconds to seconds!
                charge_duration = charge_duration_in_nano_seconds / 1000000000

            charged_energy = a_session_entry.get("chargedEnergy", 0)
            if charged_energy is None:
                charged_energy = 0
            elif not isinstance(charged_energy, Number):
                # de-noisify logs since None is a valid value for 'charged_energy' and we don't want to spam the logs with this
                charged_energy = 0
                _LOGGER.info(f"calculate_session_sums(): invalid 'charged_energy' in session entry: {a_session_entry}")

            cost = a_session_entry.get("price", 0)
            if cost is None:
                cost = 0
            elif not isinstance(cost, Number):
                # de-noisify logs since None is a valid value for 'cost' and we don't want to spam the logs with this
                cost = 0
                _LOGGER.info(f"calculate_session_sums(): invalid 'costs' in session entry: {a_session_entry}")

            _add_to_sums(vehicle_sums, a_vehicle, charge_duration, charged_energy, cost)
            _add_to_sums(loadpoint_sums, a_loadpoint, charge_duration, charged_energy, cost)

        except BaseException as exception:
            _LOGGER.info(f"calculate_session_sums(): {a_session_entry} caused: {type(exception).__name__} details: {exception}")

    json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_VEHICLES] = vehicle_sums
    json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_LOADPOINTS] = loadpoint_sums

@staticmethod
def _get_charge_duration_from_create_finish(a_session_entry: dict):
    created = a_session_entry.get("created", None)
    finished = a_session_entry.get("finished", None)
    if created is not None and finished is not None:
        try:
            start_date = parser.isoparse(created)
            end_date = parser.isoparse(finished)
            if end_date > start_date:
                delta = end_date - start_date
                return delta.total_seconds()
            else:
                _LOGGER.info(f"calculate_session_sums(): {a_session_entry['id']} invalid date range: {a_session_entry}")

        except BaseException as exception:
            _LOGGER.info(f"calculate_session_sums(): invalid 'created' or 'finished' in session entry: {a_session_entry} caused: {type(exception).__name__} details: {exception}")

    return None

@staticmethod
def _add_to_sums(a_sums_dict: dict, key: str, val_charge_duration, val_charged_energy, val_cost):
    if key is not None and len(key) > 0:
        if key not in a_sums_dict:
            a_sums_dict[key] = {"chargeDuration": 0, "chargedEnergy": 0, "cost": 0}

        a_sums_dict[key]["chargeDuration"] += val_charge_duration
        a_sums_dict[key]["chargedEnergy"] += val_charged_energy
        a_sums_dict[key]["cost"] += val_cost

class EvccApiBridge:
    def __init__(self, host: str, web_session, coordinator: DataUpdateCoordinator = None, lang: str = "en",
                 opt_password: str = None, ext_vehicle_data: bool = False, ext_meter_data: bool = False) -> None:
        # make sure we are compliant with old configurations (that does not include the schema in the host variable)
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"

        # getting the correct web socket URL...
        if host.startswith("https://"):
            self.web_socket_url = f"wss://{host[8:]}/ws"
        else:
            self.web_socket_url = f"ws://{host[7:]}/ws"

        self.ws_connected = False
        self._ws_LAST_UPDATE = -1
        self._ws_LAST_NEW_DATA_NOTIFY = -1
        self.coordinator = coordinator
        self._debounced_update_task = None
        self._debounced_additional_data_update_task = None

        self.host = host
        self._admin_password = opt_password
        self._admin_cookie_expire_datetime = None
        self._request_ext_vehicle_data = ext_vehicle_data
        self._request_ext_meter_data = ext_meter_data

        self.web_session = web_session
        self.lang_map = None
        if lang in TRANSLATIONS:
            self.lang_map = TRANSLATIONS[lang]
        else:
            self.lang_map = TRANSLATIONS["en"]

        self._TARIFF_LAST_UPDATE_QUARTER_HOUR = -1
        self._SESSIONS_LAST_UPDATE_HOUR = -1
        self._CONFIG_LAST_UPDATE = -1
        if self.coordinator is not None and hasattr(self.coordinator, 'update_interval_in_seconds_from_config_entry'):
            self._CONFIG_UPDATE_INTERVAL_IN_SECONDS = self.coordinator.update_interval_in_seconds_from_config_entry
        else:
            self._CONFIG_UPDATE_INTERVAL_IN_SECONDS = 60 * 15 # the default update will be every 15 minutes

        self._data = {}

        # by default, we do not request the tariff endpoints
        self.request_tariff_endpoints = False
        self.request_tariff_keys = []

    async def is_evcc_available(self):
        _LOGGER.debug(f"is_evcc_available(): '{self.host}' CHECKING...")
        req = f"{self.host}/api/state"
        try:
            async with self.web_session.get(url=req, ssl=False) as res:
                res.raise_for_status()
                if res.status in [200, 201, 202, 204, 205]:
                    data = await res.json()
                    if data is not None and len(data) == 0:
                        raise BaseException("NO DATA")

        except BaseException as exc:
            _LOGGER.debug(f"is_evcc_available(): check caused: {type(exc).__name__} - {exc} - Integration is not ready to be started.")
            raise exc

        _LOGGER.debug(f"is_evcc_available(): '{self.host}' is AVAILABLE")

    def enable_tariff_endpoints(self, keys: list):
        self._TARIFF_LAST_UPDATE_QUARTER_HOUR = -1
        self.request_tariff_endpoints = True
        self.request_tariff_keys = keys
        _LOGGER.debug(f"enabled tariff endpoints with keys: {keys}")

    def available_fields(self) -> int:
        return len(self._data)

    def clear_data(self, clear_evcc_data: bool = True):
        self._TARIFF_LAST_UPDATE_QUARTER_HOUR = -1
        self._SESSIONS_LAST_UPDATE_HOUR = -1
        self._CONFIG_LAST_UPDATE = -1
        self._ws_LAST_UPDATE = -1
        self._ws_LAST_NEW_DATA_NOTIFY = -1
        if clear_evcc_data:
            self._data = {}

    def ws_check_last_update(self) -> bool:
        now_time = time()
        if self._ws_LAST_UPDATE + 50 > now_time:
            _LOGGER.debug(f"ws_check_last_update(): all good! [last update: {int(now_time - self._ws_LAST_UPDATE)} sec ago]")
            return True
        else:
            _LOGGER.info(f"ws_check_last_update(): force reconnect...")
            return False

    async def connect_ws(self):
        try:
            async with self.web_session.ws_connect(self.web_socket_url) as ws:
                self.ws_connected = True
                self._ws_LAST_UPDATE = time()  # Set a grace period so the watchdog doesn't immediately kill connection
                _LOGGER.info(f"connected to websocket: {self.web_socket_url}")

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            if self._data is None or len(self._data) == 0:
                                self._TARIFF_LAST_UPDATE_QUARTER_HOUR = -1
                                self._SESSIONS_LAST_UPDATE_HOUR = -1
                                self._CONFIG_LAST_UPDATE = -1
                                await self.read_all_data()
                        except:
                            _LOGGER.info(f"could not read initial data from evcc@{self.host} - ignoring")
                            self._data = {}
                        try:
                            ws_data = msg.json()
                            if self._data is None:
                                _LOGGER.info(f"unhandled {ws_data} - since 'self._data' is NONE")
                            else:
                                for key, value in ws_data.items():
                                    if "." in key:
                                        key_parts = key.split(".")
                                        if len(key_parts) > 2:
                                            domain = key_parts[0]
                                            idx = int(key_parts[1])
                                            sub_key = key_parts[2]
                                            if domain in self._data:
                                                if len(self._data[domain]) > idx:
                                                    if not sub_key in self._data[domain][idx]:
                                                        _LOGGER.debug(f"adding '{sub_key}' to {domain}[{idx}]")
                                                    self._data[domain][idx][sub_key] = value
                                                else:
                                                    # we need to add a new entry to the list... - well
                                                    # if we get index 4 but length is only 2 we must add multiple
                                                    # empty entries to the list...
                                                    while len(self._data[domain]) <= idx:
                                                        self._data[domain].append({})

                                                    self._data[domain][idx] = {sub_key: value}
                                                    _LOGGER.debug(f"adding index {idx} to '{domain}' -> {self._data[domain][idx]}")
                                            else:
                                                _LOGGER.info(f"unhandled [{domain} not in data] 3part: {key} - ignoring: {value} data: {self._data}")
                                            # if domain == "loadpoints":
                                            #     pass
                                            # elif domain == "vehicles":
                                            #     pass
                                        elif len(key_parts) == 2:
                                            # currently only 'forcast.solar'
                                            domain = key_parts[0]
                                            sub_key = key_parts[1]
                                            if domain in self._data:
                                                if not sub_key in self._data[domain]:
                                                    _LOGGER.debug(f"adding '{sub_key}' to {domain}")
                                                self._data[domain][sub_key] = value
                                            else:
                                                _LOGGER.info(f"unhandled [{domain} not in data] 2part: {key} - domain {domain} not in self.data - ignoring: {value}")
                                        else:
                                            _LOGGER.info(f"unhandled [not parsable key] {key} - ignoring: {value}")
                                    else:
                                        if key in self._data:
                                            self._data[key] = value
                                        else:
                                            if key != "releaseNotes":
                                                self._data[key] = value
                                                _LOGGER.info(f"added '{key}' to self._data and assign: {value}")

                                # END of for loop
                                # _LOGGER.debug(f"key: {key} value: {value}")
                                self._ws_notify_coordinator_for_updated_data_debounced()

                        except Exception as e:
                            _LOGGER.info(f"Could not read JSON from: {msg} - caused {e}")
                            # Ensure we still update the coordinator even if processing failed
                            self._ws_notify_coordinator_for_updated_data_debounced()

                        # launch a task to update the session & tariff data (if needed)
                        self._ws_start_async_additional_data_update_task_if_needed()

                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        _LOGGER.debug(f"received: {msg}")
                        break
                    else:
                        _LOGGER.info(f"Other Websocket Message: {msg}")

        except asyncio.exceptions.CancelledError as cancel:
            _LOGGER.info(f"CancelledError@websocket cause by: {cancel}")
        except ClientConnectionError as con:
            _LOGGER.error(f"Could not connect to websocket: {con}")
        except BaseException as ex:
            _LOGGER.error(f"BaseException@websocket: {type(ex).__name__} - {ex}")

        self.ws_connected = False

    def _ws_start_async_additional_data_update_task_if_needed(self):
        if self._debounced_additional_data_update_task is None or self._debounced_additional_data_update_task.done():
            async def _task():
                await self.read_all_data(request_all=False, request_tariffs=True, request_sessions=True, request_config=True)
                if self.coordinator is not None and self._data_coordinator_update_needed:
                    self._ws_notify_coordinator_for_updated_data_debounced()
                # we sleep the current task for 0.5 seconds since we don't want to check with every websocket message
                # IF we must update other data...
                await asyncio.sleep(0.5)
            self._debounced_additional_data_update_task = asyncio.create_task(_task())
        else:
            # if the task is already running, we don't need to do anything...'
            pass

    def _ws_notify_coordinator_for_updated_data_debounced(self):
        if self._debounced_update_task is not None:
            self._debounced_update_task.cancel()

        async def _task():
            try:
                await asyncio.sleep(0.2)
                if self.coordinator is not None:
                    now_time = time()
                    # only update every second...
                    if now_time - self._ws_LAST_NEW_DATA_NOTIFY >= 1:
                        self._ws_LAST_NEW_DATA_NOTIFY = now_time
                        self.coordinator.async_set_updated_data(self._data)
                    else:
                        #_LOGGER.debug("_ws_update_data_debounced:task(): update was skipped due 1 sec update interval...")
                        pass

            except asyncio.CancelledError:
                #_LOGGER.debug("_ws_update_data_debounced:task(): task was cancelled (normal during reconnect)")
                pass
            except Exception as e:
                _LOGGER.info(f"_ws_update_data_debounced:task(): ERROR: {type(e).__name__}: {e}", exc_info=True)

        self._debounced_update_task = asyncio.create_task(_task())
        self._ws_LAST_UPDATE = time()

    async def read_all_data(self, request_all:bool=True,
                            request_tariffs:bool=False,
                            request_sessions:bool=False,
                            request_config:bool=False,
                            log_config_requests:bool=False) -> dict:

        #_LOGGER.debug(f"read_all_data(): from evcc@{self.host} all={request_all}, tariffs={request_tariffs}, sessions={request_sessions}, config={request_config}")
        if request_all:
            _LOGGER.debug(f"going to request 'state' data from evcc@{self.host}")
            json_resp = await self.read_state_data()
            if len(json_resp) == 0:
                return {}
        else:
            if self._data is None:
                self._data = {}
            json_resp = self._data


        self._data_coordinator_update_needed = False
        now_utc = datetime.now(timezone.utc)
        current_hour = now_utc.hour
        current_minute = now_utc.minute
        current_quarter_hour = current_minute // 15

        # additional tariffs endpoint data
        if request_all or request_tariffs:
            if self.request_tariff_endpoints:
                # we only update the tariff data once per hour...
                if self._TARIFF_LAST_UPDATE_QUARTER_HOUR != current_quarter_hour:
                    _LOGGER.debug(f"going to request 'tariff' data from evcc@{self.host}")
                    json_resp, data_was_fetched = await self.read_tariff_data(json_resp)
                    if data_was_fetched:
                        self._data_coordinator_update_needed = True
                        self._TARIFF_LAST_UPDATE_QUARTER_HOUR = current_quarter_hour
                else:
                    # we must copy the previous existing data to the new json_resp!
                    if self._data is not None and ADDITIONAL_ENDPOINTS_DATA_TARIFF in self._data:
                        json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF] = self._data[ADDITIONAL_ENDPOINTS_DATA_TARIFF]

        # additional sessions endpoint data
        if request_all or request_sessions:
            # update session data twice per hour:
            #   window A → minutes 55–59 (5 minutes before the full hour)
            #   window B → minutes 00–54 (start of the new hour)
            if current_minute >= 55:
                _sessions_slot = current_hour * 100 + 55     # e.g. 1455 at 14:55–14:59
            else:
                _sessions_slot = current_hour * 100          # e.g. 1400 at 14:00–14:54

            _sessions_should_fetch = (
                self._SESSIONS_LAST_UPDATE_HOUR == -1        # first run: fetch immediately
                or (self._SESSIONS_LAST_UPDATE_HOUR != _sessions_slot)
            )
            if _sessions_should_fetch:
                _LOGGER.debug(f"going to request 'sessions' data from evcc@{self.host}")
                json_resp, data_was_fetched = await self.read_sessions_data(json_resp)
                if data_was_fetched:
                    self._data_coordinator_update_needed = True
                    self._SESSIONS_LAST_UPDATE_HOUR = _sessions_slot
            else:
                # we must copy the previous existing data to the new json_resp!
                if self._data is not None and ADDITIONAL_ENDPOINTS_DATA_SESSIONS in self._data:
                    json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS] = self._data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS]

        # additional configuration endpoint data
        if request_all or request_config:
            now_time = time()
            if self._CONFIG_LAST_UPDATE + self._CONFIG_UPDATE_INTERVAL_IN_SECONDS <= time():
                _LOGGER.debug(f"going to request 'configuration' data from evcc@{self.host}")
                json_resp, data_was_fetched = await self.read_config_data(json_resp, log_requests=log_config_requests)
                if data_was_fetched:
                    self._data_coordinator_update_needed = True
                    self._CONFIG_LAST_UPDATE = now_time
            else:
                # we must copy the previous existing data to the new json_resp!
                if self._data is not None and ADDITIONAL_ENDPOINTS_DATA_EVCCCONF in self._data:
                    json_resp[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF] = self._data[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF]

        self._data = json_resp
        return json_resp

    async def read_state_data(self) -> dict:
        req = f"{self.host}/api/state"
        _LOGGER.debug(f"GET request: {req}")
        r_json = await _do_request(method=self.web_session.get(url=req, ssl=False, timeout=static_5sec_timeout))

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or len(str(r_json).strip()) > 0):
            return r_json
        else:
            _LOGGER.warning(f"could not read any json data from evcc@{self.host} - read: '{r_json}' -> will return an empty dict!")
            return {}

    async def read_tariff_data(self, json_resp: dict) -> dict:
        # _LOGGER.info(f"going to request additional tariff data from evcc@{self.host}")
        tariff_data_was_fetched = False
        if ADDITIONAL_ENDPOINTS_DATA_TARIFF not in json_resp:
            json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF] = {}

        for a_key in self.request_tariff_keys:
            try:
                req = f"{self.host}/api/{EP_TYPE.TARIFF.value}/{a_key}"
                _LOGGER.debug(f"GET request: {req}")
                tariff_resp = await _do_request(method=self.web_session.get(url=req, ssl=False, timeout=static_5sec_timeout))
                if tariff_resp is not None and len(tariff_resp) > 0:
                    json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF][a_key] = tariff_resp
                    tariff_data_was_fetched = True

            except Exception as err:
                _LOGGER.info(f"could not read tariff data for '{a_key}' -> '{err}'")

        return json_resp, tariff_data_was_fetched

    async def read_sessions_data(self, json_resp: dict) -> dict:
        # _LOGGER.info(f"going to request additional sessions data from evcc@{self.host}")
        session_data_was_fetched = False
        if ADDITIONAL_ENDPOINTS_DATA_SESSIONS not in json_resp:
            json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS] = {}

        try:
            req = f"{self.host}/api/{EP_TYPE.SESSIONS.value}"
            _LOGGER.debug(f"GET request: {req}")
            sessions_resp = await _do_request(method=self.web_session.get(url=req, ssl=False, timeout=static_5sec_timeout))
            if sessions_resp is not None and len(sessions_resp) > 0:
                json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_TOTAL] = len(sessions_resp)
                # raw data will exceed maximum size of 16384 bytes - so we can't store this
                # json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_RAW] = sessions_resp

                # do the math stuff...
                calculate_session_sums(sessions_resp, json_resp)
                session_data_was_fetched = True

        except BaseException as err:
            _LOGGER.info(f"could not read sessions data '{type(err).__name__}' -> {err}")

        return json_resp, session_data_was_fetched

    async def read_config_data(self, json_resp: dict, log_requests:bool=False):
        config_data_was_fetched = False
        if await self.ensure_session_is_authorized():
            if ADDITIONAL_ENDPOINTS_DATA_EVCCCONF not in json_resp:
                # creating our core data container object...
                json_resp[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF] = {}
                json_resp[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF][EVCCCONF_KEY_CONFIG] = await self._read_config_setup(log_requests)
                json_resp[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF][EVCCCONF_KEY_DATA] = {}

            # ok the configuration data MUST exis now... so we can finally fetch the states
            a_config = json_resp[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF][EVCCCONF_KEY_CONFIG]

            for a_device_type, value_list in a_config.items():
                if a_device_type == EVCCCONF_DEVICE_TYPES.VEHICLE.value and not self._request_ext_vehicle_data:
                    _LOGGER.debug(f"skipping vehicle data since 'request_ext_vehicle_data' is set to False")
                    continue

                if a_device_type == EVCCCONF_DEVICE_TYPES.METER.value and not self._request_ext_meter_data:
                    _LOGGER.debug(f"skipping meter data since 'request_ext_meter_data' is set to False")
                    continue

                for a_device_id in value_list:
                    if a_device_type not in json_resp[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF][EVCCCONF_KEY_DATA]:
                        json_resp[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF][EVCCCONF_KEY_DATA][a_device_type] = {}
                    req = f"{self.host}/api/config/devices/{a_device_type}/{a_device_id}/status"
                    if log_requests:
                        _LOGGER.debug(f"GET request: {req}")

                    a_status_resp = await _do_request(method=self.web_session.get(url=req, ssl=False, timeout=static_30sec_timeout))
                    if a_status_resp is not None and len(a_status_resp) > 0:
                        # make sure that we always use lower case device-ids
                        # compare also with the reading code in 'read_tag_configuration'
                        json_resp[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF][EVCCCONF_KEY_DATA][a_device_type][a_device_id.lower()] = a_status_resp
                        if not config_data_was_fetched:
                            config_data_was_fetched = True
                        if log_requests:
                            _LOGGER.debug(f"Response received for {req}: {a_status_resp}")

            _LOGGER.debug(f"read_config_data(): configuration data read {list(json_resp[ADDITIONAL_ENDPOINTS_DATA_EVCCCONF][EVCCCONF_KEY_DATA].keys())}")

        return json_resp, config_data_was_fetched

    async def _read_config_setup(self, log_requests:bool=False):
        the_configuration = {}
        # ok we must first fetch (once) the available configuration entities!
        for a_object_type in EVCCCONF_OBJECT_HIERARCHY.keys():
            if len(EVCCCONF_OBJECT_HIERARCHY[a_object_type]) > 0:
                the_configuration[a_object_type] = {}
                for a_sub_type in EVCCCONF_OBJECT_HIERARCHY[a_object_type]:
                    req = f"{self.host}/api/config/{a_object_type}/{a_sub_type}"
                    if log_requests:
                        _LOGGER.debug(f"GET request: {req}")
                    config_resp = await _do_request(method=self.web_session.get(url=req, ssl=False, timeout=static_30sec_timeout))
                    if config_resp is not None and len(config_resp) > 0:
                        the_configuration[a_object_type][a_sub_type] = config_resp
                        if log_requests:
                            _LOGGER.debug(f"Response received for {req}: {config_resp}")
                    else:
                        # ensure that at least something exists for the sub-type
                        _LOGGER.info(f"No configuration found for sub-object type '{a_object_type}/{a_sub_type}', creating empty entry")
                        the_configuration[a_object_type][a_sub_type] = {}
            else:
                req = f"{self.host}/api/config/{a_object_type}"
                if log_requests:
                    _LOGGER.debug(f"GET request: {req}")
                config_resp = await _do_request(method=self.web_session.get(url=req, ssl=False, timeout=static_30sec_timeout))
                if config_resp is not None and len(config_resp) > 0:
                    the_configuration[a_object_type] = config_resp
                    if log_requests:
                        _LOGGER.debug(f"Response received for {req}: {config_resp}")
                else:
                    # ensure that at least something exists for the object-type (e.g. when there is
                    # no loadpoints)
                    _LOGGER.info(f"No configuration found for object type '{a_object_type}', creating empty entry")
                    the_configuration[a_object_type] = {}

        # just as object reference...
        # a_sample_config = {
        #     "devices": {
        #         "vehicle": [
        #             {
        #                 "config": {
        #                     "icon": "ford-mustang-mach-e",
        #                     "title": "MachE IS HERE"
        #                 },
        #                 "name": "ford_mach_e",
        #                 "type": "template"
        #             }
        #         ],
        #         "charger": [
        #             {
        #                 "config": {
        #                     "icon": "waterheater"
        #                 },
        #                 "name": "heatpump-water_ha_switch",
        #                 "type": "template"
        #             },
        #             {
        #                 "name": "go-e",
        #                 "type": "template"
        #             },
        #             {
        #                 "config": {
        #                     "icon": "heatexchange"
        #                 },
        #                 "name": "pool-shelly_switch",
        #                 "type": "template"
        #             },
        #             {
        #                 "config": {
        #                     "icon": "compute"
        #                 },
        #                 "name": "garden-shelly_switch",
        #                 "type": "template"
        #             }
        #         ],
        #         "meter": [
        #             {
        #                 "name": "SENEC.bat",
        #                 "type": "template"
        #             },
        #             {
        #                 "name": "TIBBER.grid",
        #                 "type": "template"
        #             },
        #             {
        #                 "name": "SENEC.grid",
        #                 "type": "template"
        #             },
        #             {
        #                 "name": "SENEC.pv",
        #                 "type": "template"
        #             }
        #         ],
        #         "circuit": [
        #             {
        #                 "config": {
        #                     "title": "Hausanschluss"
        #                 },
        #                 "name": "main"
        #             }
        #         ]
        #     },
        #     "site": {
        #         "title": "Home",
        #         "grid": "TIBBER.grid",
        #         "pv": [
        #             "SENEC.pv"
        #         ],
        #         "battery": [
        #             "SENEC.bat"
        #         ],
        #         "aux": None,
        #         "ext": [
        #             "SENEC.grid"
        #         ]
        #     },
        #     "loadpoints": [
        #         {
        #             "name": "lp-1",
        #             "charger": "go-e",
        #             "title": "HH-7",
        #             "defaultMode": "",
        #             "priority": 3,
        #             "phasesConfigured": 0,
        #             "minCurrent": 6,
        #             "maxCurrent": 25,
        #             "smartCostLimit": -0.11,
        #             "smartFeedInPriorityLimit": None,
        #             "planEnergy": 0,
        #             "planTime": "0001-01-01T00:00:00Z",
        #             "planPrecondition": 0,
        #             "batteryBoostLimit": 100,
        #             "limitEnergy": 0,
        #             "limitSoc": 0,
        #             "planStrategy": {
        #                 "continuous": False,
        #                 "precondition": 0
        #             },
        #             "thresholds": {
        #                 "enable": {
        #                     "delay": 30000000000,
        #                     "threshold": 0
        #                 },
        #                 "disable": {
        #                     "delay": 90000000000,
        #                     "threshold": 0
        #                 }
        #             },
        #             "soc": {
        #                 "poll": {
        #                     "mode": "charging",
        #                     "interval": 3600000000000
        #                 },
        #                 "estimate": None
        #             }
        #         },
        #         {
        #             "name": "lp-2",
        #             "charger": "pool-shelly_switch",
        #             "title": "Pool",
        #             "defaultMode": "",
        #             "priority": 4,
        #             "phasesConfigured": 1,
        #             "minCurrent": 5,
        #             "maxCurrent": 5,
        #             "smartCostLimit": -0.11,
        #             "smartFeedInPriorityLimit": None,
        #             "planEnergy": 0,
        #             "planTime": "0001-01-01T00:00:00Z",
        #             "planPrecondition": 0,
        #             "batteryBoostLimit": 100,
        #             "limitEnergy": 0,
        #             "limitSoc": 0,
        #             "planStrategy": {
        #                 "continuous": False,
        #                 "precondition": 0
        #             },
        #             "thresholds": {
        #                 "enable": {
        #                     "delay": 300000000000,
        #                     "threshold": 0
        #                 },
        #                 "disable": {
        #                     "delay": 300000000000,
        #                     "threshold": 0
        #                 }
        #             },
        #             "soc": {
        #                 "poll": {
        #                     "mode": "charging",
        #                     "interval": 3600000000000
        #                 },
        #                 "estimate": None
        #             }
        #         },
        #         {
        #             "name": "lp-3",
        #             "charger": "garden-shelly_switch",
        #             "title": "Gartenpumpe",
        #             "defaultMode": "",
        #             "priority": 5,
        #             "phasesConfigured": 1,
        #             "minCurrent": 5,
        #             "maxCurrent": 7,
        #             "smartCostLimit": -0.11,
        #             "smartFeedInPriorityLimit": None,
        #             "planEnergy": 0,
        #             "planTime": "0001-01-01T00:00:00Z",
        #             "planPrecondition": 0,
        #             "batteryBoostLimit": 100,
        #             "limitEnergy": 0,
        #             "limitSoc": 0,
        #             "planStrategy": {
        #                 "continuous": False,
        #                 "precondition": 0
        #             },
        #             "thresholds": {
        #                 "enable": {
        #                     "delay": 30000000000,
        #                     "threshold": 0
        #                 },
        #                 "disable": {
        #                     "delay": 600000000000,
        #                     "threshold": 0
        #                 }
        #             },
        #             "soc": {
        #                 "poll": {
        #                     "mode": "charging",
        #                     "interval": 3600000000000
        #                 },
        #                 "estimate": None
        #             }
        #         },
        #         {
        #             "name": "lp-4",
        #             "charger": "heatpump-water_ha_switch",
        #             "title": "Warmwasser-Boost",
        #             "defaultMode": "",
        #             "priority": 1,
        #             "phasesConfigured": 1,
        #             "minCurrent": 13.48,
        #             "maxCurrent": 13.48,
        #             "smartCostLimit": -0.11,
        #             "smartFeedInPriorityLimit": None,
        #             "planEnergy": 0,
        #             "planTime": "0001-01-01T00:00:00Z",
        #             "planPrecondition": 0,
        #             "batteryBoostLimit": 100,
        #             "limitEnergy": 0,
        #             "limitSoc": 0,
        #             "planStrategy": {
        #                 "continuous": False,
        #                 "precondition": 0
        #             },
        #             "thresholds": {
        #                 "enable": {
        #                     "delay": 1500000000000,
        #                     "threshold": 0
        #                 },
        #                 "disable": {
        #                     "delay": 300000000000,
        #                     "threshold": 0
        #                 }
        #             },
        #             "soc": {
        #                 "poll": {
        #                     "mode": "charging",
        #                     "interval": 3600000000000
        #                 },
        #                 "estimate": None
        #             }
        #         }
        #     ],
        #     "tariff": {
        #         "grid": "",
        #         "feedIn": "",
        #         "co2": "",
        #         "planner": "",
        #         "solar": None
        #     }
        # }

        # in the 'site' object, we can see which 'meter' is from which type:
        # grid, pv, battery, aux and ext (but currently we don't use this info (yet))

        # since the_configuration has been created on basis of the EVCCCONF_OBJECT_HIERARCHY
        # we are sure that "site", "loadpoints" and "devices" are present!
        meter_to_site_key = {}
        if EVCCCONF_SITE in the_configuration:
            for key, value in the_configuration[EVCCCONF_SITE].items():
                if value is None:
                    continue

                if isinstance(value, list):
                    for meter_name in value:
                        meter_to_site_key[meter_name] = key
                else:
                    meter_to_site_key[value] = key

        # generate a lookup also for the 'chargers' - since a charger is assigned to a
        # loadpoint (1:1)
        if EVCCCONF_LOADPOINTS in the_configuration:
            loadpoint_by_charger = {
                loadpoint[EVCCCONF_DEVICE_TYPES.CHARGER.value]: loadpoint
                for loadpoint in the_configuration[EVCCCONF_LOADPOINTS]
            }
        else:
            loadpoint_by_charger = {}

        # so 'the_configuration' object should contain the keys:"devices", "site", "loadpoints" and "tariff"
        # currently we are ONLY interested in the devices!
        a_result = {}
        if EVCCCONF_DEVICES in the_configuration:
            for category, items in the_configuration[EVCCCONF_DEVICES].items():
                if category == EVCCCONF_DEVICE_TYPES.METER.value:
                    a_result[category] = {
                        item["name"]: meter_to_site_key.get(item["name"])
                        for item in items
                    }
                elif category == EVCCCONF_DEVICE_TYPES.CHARGER.value:
                    a_result[category] = {
                        item["name"]: loadpoint_by_charger.get(item["name"])
                        for item in items
                    }
                else:
                    a_result[category] = [
                        item["name"]
                        for item in items
                    ]
                # if we additionally need the loadpoint names (=id's)... we can use this line:
                # a_result["loadpoints"] = [lp["name"] for lp in a_conf["loadpoints"]]

        _LOGGER.debug(f"_read_config_setup(): configuration setup read successfully {list(a_result.keys())}")
        return a_result

    async def force_config_update(self):
        _LOGGER.debug(f"force_config_update(): forcing config update")
        self._CONFIG_LAST_UPDATE = -1
        await self.read_all_data(request_all=False, request_config=True)
        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(self._data)

    async def ensure_session_is_authorized(self):
        if self._admin_password is not None:

            # check check-implementation...
            if self._admin_cookie_expire_datetime is not None:
                if self._admin_cookie_expire_datetime > dt_util.utcnow():
                    return True

            # the default code will ask the evcc-backend if our session is authorized?!
            # I assume this will happen with every HA restart...
            try:
                async with self.web_session.get(url=f"{self.host}/api/auth/status", ssl=False, timeout=static_5sec_timeout) as resp_status:
                    if resp_status.status == 200:
                        status_response_from_evcc_server_if_seesion_is_authorized = await resp_status.json()
                    else:
                        status_response_from_evcc_server_if_seesion_is_authorized = False

                    if status_response_from_evcc_server_if_seesion_is_authorized is not True:
                        # we need to authenticate...
                        _LOGGER.debug(f"ensure_session_is_authorized(): auth status returned {resp_status.status} - trying to authenticate")
                        async with self.web_session.post(url=f"{self.host}/api/auth/login", json={"password": self._admin_password}, ssl=False, timeout=static_5sec_timeout) as resp_auth:
                            if resp_auth.status != 200:
                                _LOGGER.warning(f"ensure_session_is_authorized(): authentication failed with status {resp_auth.status}")
                                return False
                            else:
                                if resp_auth.headers is not None:
                                    # resp_auth.headers is a 'CIMultiDict' - this means, the key is case_insensitive!!!
                                    # so no matter if we check for "Set-Cookie" or "set-cookie" or "SET-COOKIE"
                                    set_cookie_str = resp_auth.headers.get("Set-Cookie", None)
                                    if set_cookie_str is not None:
                                        # set_cookie_str = 'auth=XXXX; Path=/; Expires=Thu, 30 Jul 2026 16:38:18 GMT; HttpOnly; SameSite=Strict'
                                        for a_statement in set_cookie_str.split(";"):
                                            if a_statement is not None and a_statement.strip().lower().startswith("expires="):
                                                # we need to parse the expiration date of the cookie... this will do the
                                                # 'email.utils.parsedate_to_datetime' and
                                                # 'homeassistant.util.dt' for us!
                                                a_expire_date = a_statement.strip().split('=')[1]
                                                self._admin_cookie_expire_datetime = dt_util.as_utc(parsedate_to_datetime(a_expire_date))
                                                if self._admin_cookie_expire_datetime > dt_util.utcnow():
                                                    _LOGGER.info(f"ensure_session_is_authorized(): authentication successful")
                                                    if self.coordinator is not None:
                                                        await self.coordinator.save_cookies()
                                                    return True

                                # if we could not read the set-cookie header... or the expiration date... we assume the login
                                # failed...
                                _LOGGER.warning(f"ensure_session_is_authorized(): authentication failed with no Set-Cookie header")
                                return False
                    else:
                        if self._admin_cookie_expire_datetime is None:
                            # we must parse the expiration date of the cookie from our jar!
                            for a_cookie in self.web_session.cookie_jar:
                                if a_cookie.get("domain", "UNKNOWN-DOMAIN") in self.host and a_cookie.key == "auth":
                                    # this is quite a simple check if this 'auth' cookie belongs to our host...
                                    # but it should be enough...
                                    a_expire_date = a_cookie.get("expires", None)
                                    if a_expire_date is not None and len(a_expire_date) > 0:
                                        self._admin_cookie_expire_datetime = dt_util.as_utc(parsedate_to_datetime(a_expire_date))
                                        if self._admin_cookie_expire_datetime > dt_util.utcnow():
                                            _LOGGER.info(f"ensure_session_is_authorized(): session already authorized AND '_admin_cookie_expire_datetime' IS SET")
                                            return True

                        _LOGGER.info(f"ensure_session_is_authorized(): session already authorized - but no '_admin_cookie_expire_datetime' is set :-(")
                        return True

            except BaseException as ex:
                _LOGGER.warning(f"ensure_session_is_authorized(): caused {type(ex).__name__} -> {ex}")
        else:
            return False

    async def press_tag(self, a_tag: Tag, value, idx: str = None) -> dict:
        ret = {}

        # 'configuration' types MUST be authorized
        if a_tag.type == EP_TYPE.EVCCCONF:
            if not await self.ensure_session_is_authorized():
                _LOGGER.warning(f"press_tag(): could not authorize session - skipping: {a_tag.json_key}, value: {value}, idx: {idx}")
                ret[a_tag.json_key] = False
                return ret

        # check, if we must "re-write" the type...
        if hasattr(a_tag, "write_type") and a_tag.write_type is not None:
            final_type = a_tag.write_type
        else:
            final_type = a_tag.type

        # if there is NO-PAYLOAD for a TRIGGER
        if value == IS_TRIGGER:
            # we will just post "no-data" to the f"{host}/api/{a_tag.write_key}"
            ret[a_tag.json_key] = await self.press_trigger_key(a_tag.write_key, a_tag.expected_http_status_response)

        elif final_type == EP_TYPE.LOADPOINTS and idx is not None:
            ret[a_tag.json_key] = await self.press_loadpoint_key(idx, a_tag.write_key, value)

        elif final_type == EP_TYPE.VEHICLES:
            # before we can write something to the vehicle endpoints, we must know the vehicle_id!
            # -> so we have to grab from the loadpoint the current vehicle!
            if self._data is not None and len(self._data) > 0 and JSONKEY_LOADPOINTS in self._data:
                try:
                    int_idx = int(idx) - 1
                    vehicle_id = self._data[JSONKEY_LOADPOINTS][int_idx][Tag.LP_VEHICLENAME.json_key]
                    if vehicle_id is not None:
                        ret[a_tag.json_key] = await self.press_vehicle_key(vehicle_id, a_tag.write_key, value)

                except Exception as err:
                    _LOGGER.info(f"could not find a connected vehicle at loadpoint: {idx}")

        return ret

    async def press_trigger_key(self, write_key, expected_response_http_status:int=None) -> dict:
        req = f"{self.host}/api/{write_key}"
        _LOGGER.debug(f"press_trigger_key(): POST request: {req}")
        resp = await _do_request(method=self.web_session.post(url=req, ssl=False, timeout=static_5sec_timeout), return_raw_client_response=True)
        raw_resp = resp.get(RAW_CLIENT_RESPONSE_KEY, None)
        if raw_resp is not None and expected_response_http_status is not None:
            if raw_resp.status == expected_response_http_status:
                return True
            else:
                _LOGGER.warning(f"press_trigger_key(): unexpected response status: IS: {raw_resp.status} / EXPECTED: {expected_response_http_status} - skipping: {write_key}")
                return False
        else:
            _LOGGER.warning(f"press_trigger_key(): need to handle response for '{write_key}' -> received: {resp}")
            return False

    async def press_loadpoint_key(self, lp_idx, write_key, value) -> dict:
        # idx will start with 1!
        if isinstance(value, (bool, int, float)):
            value = str(value).lower()
        elif value is not None:
            value = str(value)

        _LOGGER.info(f"going to press a button with payload '{value}' for key '{write_key}' to evcc-loadpoint{lp_idx}@{self.host}")
        if value is None:
            if write_key == Tag.LP_DETECTVEHICLE.write_key:
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/vehicle"
                _LOGGER.debug(f"PATCH request: {req}")
                r_json = await _do_request(method=self.web_session.patch(url=req, ssl=False, timeout=static_5sec_timeout))
            else:
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/{write_key}"
                _LOGGER.debug(f"DELETE request: {req}")
                r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False, timeout=static_5sec_timeout))
        else:
            req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method=self.web_session.post(url=req, ssl=False, timeout=static_5sec_timeout))

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def press_vehicle_key(self, vehicle_id: str, write_key, value) -> dict:
        if isinstance(value, (bool, int, float)):
            value = str(value).lower()
        elif value is not None:
            value = str(value)

        _LOGGER.info(f"going to press a button with payload '{value}' for key '{write_key}' to evcc-vehicle{vehicle_id}@{self.host}")
        r_json = None
        if value is None:
            if write_key == Tag.VEHICLEPLANSDELETE.write_key:
                req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/{write_key}"
                _LOGGER.debug(f"DELETE request: {req}")
                r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False, timeout=static_5sec_timeout))
            else:
                pass
        else:
            req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method=self.web_session.post(url=req, ssl=False, timeout=static_5sec_timeout))

        if r_json is not None:
            if (hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str)):
                r_json[write_key] = "OK"
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def write_tag(self, tag: Tag, value, idx_str: str = None) -> dict:
        ret = {}
        if hasattr(tag, "write_type") and tag.write_type is not None:
            final_type = tag.write_type
        else:
            final_type = tag.type

        if final_type == EP_TYPE.SITE:
            ret[tag.json_key] = await self.write_site_key(tag.write_key, value)

        elif final_type == EP_TYPE.LOADPOINTS and idx_str is not None:
            ret[tag.json_key] = await self.write_loadpoint_key(idx_str, tag.write_key, value)

        elif final_type == EP_TYPE.VEHICLES:
            # before we can write something to the vehicle endpoints, we must know the vehicle_id!
            # -> so we have to grab from the loadpoint the current vehicle!
            if self._data is not None and len(self._data) > 0 and JSONKEY_LOADPOINTS in self._data:
                try:
                    int_idx = int(idx_str) - 1
                    vehicle_id = self._data[JSONKEY_LOADPOINTS][int_idx][Tag.LP_VEHICLENAME.json_key]
                    if vehicle_id is not None:
                        ret[tag.json_key] = await self.write_vehicle_key(vehicle_id, tag.write_key, value)

                except Exception as err:
                    _LOGGER.info(f"could not find a connected vehicle at loadpoint: {idx_str}")

        return ret

    async def write_site_key(self, write_key, value) -> dict:
        if isinstance(value, (bool, int, float)):
            value = str(value).lower()
        elif value is not None:
            value = str(value)

        _LOGGER.info(f"going to write '{value}' for key '{write_key}' to evcc-site@{self.host}")
        r_json = None
        if value is None:
            req = f"{self.host}/api/{write_key}"
            _LOGGER.debug(f"DELETE request: {req}")
            r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False, timeout=static_5sec_timeout))
        else:
            req = f"{self.host}/api/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method=self.web_session.post(url=req, ssl=False, timeout=static_5sec_timeout))

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def write_loadpoint_key(self, lp_idx_str, write_key, value) -> dict:
        # lp_idx_str will start with 1!
        if isinstance(value, (bool, int, float)):
            value = str(value).lower()
        elif value is not None:
            value = str(value)

        _LOGGER.info(f"going to write '{value}' for key '{write_key}' to evcc-loadpoint{lp_idx_str}@{self.host}")
        r_json = None
        if value is None:
            # DELETE...
            req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx_str}/{write_key}"
            _LOGGER.debug(f"DELETE request: {req}")
            r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False, timeout=static_5sec_timeout))
        else:

            if not write_key.startswith("plan/strategy"):
                # default handling for all other keys...
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx_str}/{write_key}/{value}"
                _LOGGER.debug(f"POST request: {req}")
                r_json = await _do_request(method=self.web_session.post(url=req, ssl=False, timeout=static_5sec_timeout))

            else:
                # VERY SPECIAL HANDLING for 'plan/strategy' write process... [this is still quite a HACK!]
                if self._data is not None and len(self._data) > 0 and JSONKEY_LOADPOINTS in self._data:
                    try:
                        array_idx = int(lp_idx_str) - 1
                        lp_object = self._data[JSONKEY_LOADPOINTS][array_idx]
                        if "effectivePlanStrategy" in lp_object:

                            # 1'st we must create the payload...
                            payload_json = lp_object["effectivePlanStrategy"].copy()
                            if write_key == "plan/strategy/continuous":
                                # the switch code will give us "1" or "0"... (and we need to convert it to a boolean)
                                payload_json["continuous"] = value == "1"
                            else:
                                # make sure that the precondition is an integer...
                                payload_json["precondition"] = int(value)

                            # setting the final write_key to 'plan/strategy'...
                            # -> this is the only way to write the 'plan/strategy' to the 'vehicle' or to the 'loadpoint'!
                            write_key = "plan/strategy"

                            # 2'nd we must check if we need to write the 'plan/strategy' to the 'vehicle' or to the 'loadpoint'!
                            vehicle_id = lp_object[Tag.LP_VEHICLENAME.json_key]
                            if vehicle_id is not None:
                                req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/{write_key}"
                            else:
                                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx_str}/{write_key}"

                            _LOGGER.debug(f"POST request: {req} - sending payload: {payload_json}")
                            r_json = await _do_request(method=self.web_session.post(url=req, json=payload_json, ssl=False, timeout=static_5sec_timeout))
                        else:
                            _LOGGER.info(f"no previous 'effectivePlanStrategy' object found for loadpoint: {lp_idx_str} - {lp_object}")

                    except Exception as err:
                        _LOGGER.info(f"could not find a connected vehicle at loadpoint: {lp_idx_str}")

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str, dict))):
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def write_vehicle_key(self, vehicle_id: str, write_key, value) -> dict:
        if isinstance(value, (bool, int, float)):
            value = str(value).lower()
        else:
            value = str(value)

        _LOGGER.info(f"going to write '{value}' for key '{write_key}' to evcc-vehicle{vehicle_id}@{self.host}")
        req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/{write_key}/{value}"
        _LOGGER.debug(f"POST request: {req}")
        r_json = await _do_request(method=self.web_session.post(url=req, ssl=False, timeout=static_5sec_timeout))

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def write_loadpoint_plan(self, idx: str, energy: str, rfc_date: str):
        try:
            r_json = None
            if energy is not None and rfc_date is not None:
                # WRITE PLAN...
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{idx}/plan/energy/{energy}/{rfc_date}"
                _LOGGER.debug(f"POST request: {req}")
                r_json = await _do_request(method=self.web_session.post(url=req, ssl=False, timeout=static_5sec_timeout))
            else:
                # DELETE PLAN...
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{idx}/plan/energy"
                _LOGGER.debug(f"DELETE request: {req}")
                r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False, timeout=static_5sec_timeout))

            if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
                return r_json
            else:
                return {"err": "no response from evcc"}

        except Exception as err:
            _LOGGER.info(f"could not write to loadpoint: {idx}")

    async def write_vehicle_plan(self, vehicle_id:str, soc:str, rfc_date:str, precondition: int | None = None):
        if vehicle_id is not None:
            try:
                r_json = None
                if soc is not None and rfc_date is not None:
                    # WRITE PLAN...
                    req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/plan/soc/{soc}/{rfc_date}"
                    if precondition is not None and precondition > 0:
                        req += f"?precondition={precondition}"
                    _LOGGER.debug(f"POST request: {req}")
                    r_json = await _do_request(method=self.web_session.post(url=req, ssl=False, timeout=static_5sec_timeout))
                else:
                    # DELETE PLAN...
                    req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/plan/soc"
                    _LOGGER.debug(f"DELETE request: {req}")
                    r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False, timeout=static_5sec_timeout))

                if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
                    return r_json
                else:
                    return {"err": "no response from evcc"}

            except Exception as err:
                _LOGGER.error(f"could not write vehicle plan for vehicle: {vehicle_id}, error: {err}")
                return {"err": f"could not write vehicle plan: {err}"}
