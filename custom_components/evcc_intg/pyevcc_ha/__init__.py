import asyncio
import logging
from datetime import datetime, timezone
from json import JSONDecodeError
from numbers import Number
from typing import Callable

import aiohttp
from aiohttp import ClientResponseError, ClientConnectionError, ClientError
from dateutil import parser
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.evcc_intg.pyevcc_ha.const import (
    TRANSLATIONS,
    JSONKEY_LOADPOINTS,
    JSONKEY_VEHICLES,
    ADDITIONAL_ENDPOINTS_DATA_TARIFF,
    ADDITIONAL_ENDPOINTS_DATA_SESSIONS,
    SESSIONS_KEY_RAW,
    SESSIONS_KEY_TOTAL,
    SESSIONS_KEY_VEHICLES,
    SESSIONS_KEY_LOADPOINTS
)
from custom_components.evcc_intg.pyevcc_ha.keys import EP_TYPE, Tag, IS_TRIGGER

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def _do_request(method: Callable) -> dict:
    try:
        async with method as res:
            try:
                if 199 < res.status < 300:
                    try:
                        if "application/json" in res.content_type.lower():
                            try:
                                data = await res.json()
                                # check if the data is a dict with a single key "result" - this 'result' container
                                # will be removed in the future [https://github.com/evcc-io/evcc/pull/22299]
                                if isinstance(data, dict) and "result" in data and len(data) == 1:
                                    data = data["result"]
                                return data

                            except JSONDecodeError as json_exc:
                                _LOGGER.warning(f"APP-API: JSONDecodeError while 'await res.json(): {json_exc} [caused by {res.request_info.method} {res.request_info.url}]")

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
            if a_vehicle is None or len(a_vehicle) == 0 or a_loadpoint is None or len(a_loadpoint) == 0:
                _LOGGER.info(f"calculate_session_sums(): missing a key in session entry: {a_session_entry}")

            created = a_session_entry.get("created", None)
            finished = a_session_entry.get("finished", None)
            if created is not None and finished is not None:
                try:
                    delta = parser.isoparse(finished) - parser.isoparse(created)
                    charge_duration = delta.total_seconds()
                    #_LOGGER.debug(f"calculate_session_sums(): {a_session_entry["id"]} {charge_duration}")

                except BaseException as exception:
                    _LOGGER.info(f"calculate_session_sums(): invalid 'created' or 'finished' in session entry: {a_session_entry} caused: {type(exception).__name__} details: {exception}")
                    charge_duration = 0
            else:
                charge_duration = a_session_entry.get("chargeDuration", 0)
                if charge_duration is None or not isinstance(charge_duration, Number):
                    charge_duration = 0
                    _LOGGER.info(f"calculate_session_sums(): invalid 'charge_duration' in session entry: {a_session_entry}")

            charged_energy = a_session_entry.get("chargedEnergy", 0)
            if charged_energy is None or not isinstance(charged_energy, Number):
                charged_energy = 0
                _LOGGER.info(f"calculate_session_sums(): invalid 'charged_energy' in session entry: {a_session_entry}")

            cost = a_session_entry.get("price", 0)
            if cost is None or not isinstance(cost, Number):
                cost = 0
                _LOGGER.info(f"calculate_session_sums(): invalid 'costs' in session entry: {a_session_entry}")

            _add_to_sums(vehicle_sums, a_vehicle, charge_duration, charged_energy, cost)
            _add_to_sums(loadpoint_sums, a_loadpoint, charge_duration, charged_energy, cost)

        except BaseException as exception:
            _LOGGER.info(f"calculate_session_sums(): {a_session_entry} caused: {type(exception).__name__} details: {exception}")

    json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_VEHICLES] = vehicle_sums
    json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_LOADPOINTS] = loadpoint_sums

@staticmethod
def _add_to_sums(a_sums_dict: dict, key: str, val_charge_duration, val_charged_energy, val_cost):
    if key is not None and len(key) > 0:
        if key not in a_sums_dict:
            a_sums_dict[key] = {"chargeDuration": 0, "chargedEnergy": 0, "cost": 0}

        a_sums_dict[key]["chargeDuration"] += val_charge_duration
        a_sums_dict[key]["chargedEnergy"] += val_charged_energy
        a_sums_dict[key]["cost"] += val_cost

class EvccApiBridge:
    def __init__(self, host: str, web_session, coordinator: DataUpdateCoordinator = None, lang: str = "en") -> None:
        # make sure we are compliant with old configurations (that does not include the schema in the host variable)
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"

        # getting the correct web socket URL...
        if host.startswith("https://"):
            self.web_socket_url = f"wss://{host[8:]}/ws"
        else:
            self.web_socket_url = f"ws://{host[7:]}/ws"

        self.ws_connected = False
        self.coordinator = coordinator
        self._debounced_update_task = None

        self.host = host
        self.web_session = web_session
        self.lang_map = None
        if lang in TRANSLATIONS:
            self.lang_map = TRANSLATIONS[lang]
        else:
            self.lang_map = TRANSLATIONS["en"]

        self._TARIFF_LAST_UPDATE_HOUR = -1
        self._SESSIONS_LAST_UPDATE_HOUR = -1
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
        self._TARIFF_LAST_UPDATE_HOUR = -1
        self.request_tariff_endpoints = True
        self.request_tariff_keys = keys
        _LOGGER.debug(f"enabled tariff endpoints with keys: {keys}")

    def available_fields(self) -> int:
        return len(self._data)

    def clear_data(self):
        self._TARIFF_LAST_UPDATE_HOUR = -1
        self._SESSIONS_LAST_UPDATE_HOUR = -1
        self._data = {}

    async def ws_update_tariffs_if_required(self):
        """if we are in websocket mode, then we must (at least once each hour) update the tariff-data - we call
        this method in the watchdog to make sure that we have the latest data available!
        """
        if self.request_tariff_endpoints and self._TARIFF_LAST_UPDATE_HOUR != datetime.now(timezone.utc).hour:
            await self.read_all_data(request_all=False, request_tariffs=True)

    async def ws_update_sessions_if_required(self):
        """if we are in websocket mode, then we must (at least once each hour) update the sessions-data - we call
        this method in the watchdog to make sure that we have the latest data available!
        """
        if self._SESSIONS_LAST_UPDATE_HOUR != datetime.now(timezone.utc).hour:
            await self.read_all_data(request_all=False, request_sessions=True)

    async def connect_ws(self):
        try:
            async with self.web_session.ws_connect(self.web_socket_url) as ws:
                self.ws_connected = True
                _LOGGER.info(f"connected to websocket: {self.web_socket_url}")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            if self._data is None or len(self._data) == 0:
                                self._TARIFF_LAST_UPDATE_HOUR = -1
                                self._SESSIONS_LAST_UPDATE_HOUR = -1
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
                                                _LOGGER.info(f"'added {key}' to self._data and assign: {value}")


                                # END of for loop
                                # _LOGGER.debug(f"key: {key} value: {value}")
                                if self._debounced_update_task is not None:
                                    self._debounced_update_task.cancel()
                                self._debounced_update_task = asyncio.create_task(self._debounce_coordinator_update())

                        except Exception as e:
                            _LOGGER.info(f"Could not read JSON from: {msg} - caused {e}")

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

    async def _debounce_coordinator_update(self):
        await asyncio.sleep(0.3)
        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(self._data)

    async def read_all_data(self, request_all:bool=True, request_tariffs:bool=False, request_sessions:bool=False) -> dict:
        if request_all:
            _LOGGER.debug(f"going to read all data from evcc@{self.host}")
            req = f"{self.host}/api/state"
            _LOGGER.debug(f"GET request: {req}")
            json_resp = await _do_request(method=self.web_session.get(url=req, ssl=False))

            if json_resp is not None and len(json_resp) == 0:
                _LOGGER.info(f"could not read data from evcc@{self.host} - using empty data")
        else:
            if self._data is None:
                self._data = {}
            json_resp = self._data

        current_hour = datetime.now(timezone.utc).hour
        if request_all or request_tariffs:
            if self.request_tariff_endpoints:
                _LOGGER.debug(f"going to request tariff data from evcc@{self.host}")
                # we only update the tariff data once per hour...
                if self._TARIFF_LAST_UPDATE_HOUR != current_hour:
                    json_resp = await self.read_tariff_data(json_resp)
                    self._TARIFF_LAST_UPDATE_HOUR = current_hour
                else:
                    # we must copy the previous existing data to the new json_resp!
                    if self._data is not None and ADDITIONAL_ENDPOINTS_DATA_TARIFF in self._data:
                        json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF] = self._data[ADDITIONAL_ENDPOINTS_DATA_TARIFF]

        if request_all or request_sessions:
            _LOGGER.debug(f"going to request sessions data from evcc@{self.host}")
            # we only update the sessions data once per hour...
            if self._SESSIONS_LAST_UPDATE_HOUR != current_hour:
                json_resp = await self.read_sessions_data(json_resp)
                self._SESSIONS_LAST_UPDATE_HOUR = current_hour
            else:
                # we must copy the previous existing data to the new json_resp!
                if self._data is not None and ADDITIONAL_ENDPOINTS_DATA_SESSIONS in self._data:
                    json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS] = self._data[ADDITIONAL_ENDPOINTS_DATA_SESSIONS]

        self._data = json_resp
        return json_resp

    async def read_tariff_data(self, json_resp: dict) -> dict:
        # _LOGGER.info(f"going to request additional tariff data from evcc@{self.host}")
        if ADDITIONAL_ENDPOINTS_DATA_TARIFF not in json_resp:
            json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF] = {}

        for a_key in self.request_tariff_keys:
            try:
                req = f"{self.host}/api/{EP_TYPE.TARIFF.value}/{a_key}"
                _LOGGER.debug(f"GET request: {req}")
                tariff_resp = await _do_request(method=self.web_session.get(url=req, ssl=False))
                if tariff_resp is not None and len(tariff_resp) > 0:
                    json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF][a_key] = tariff_resp

            except Exception as err:
                _LOGGER.info(f"could not read tariff data for '{a_key}' -> '{err}'")

        return json_resp

    async def read_sessions_data(self, json_resp: dict) -> dict:
        # _LOGGER.info(f"going to request additional sessions data from evcc@{self.host}")
        if ADDITIONAL_ENDPOINTS_DATA_SESSIONS not in json_resp:
            json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS] = {}

        try:
            req = f"{self.host}/api/{EP_TYPE.SESSIONS.value}"
            _LOGGER.debug(f"GET request: {req}")
            sessions_resp = await _do_request(method=self.web_session.get(url=req, ssl=False))
            if sessions_resp is not None and len(sessions_resp) > 0:
                json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_TOTAL] = len(sessions_resp)
                # raw data will exceed maximum size of 16384 bytes - so we can't store this
                # json_resp[ADDITIONAL_ENDPOINTS_DATA_SESSIONS][SESSIONS_KEY_RAW] = sessions_resp

                # do the math stuff...
                calculate_session_sums(sessions_resp, json_resp)

        except BaseException as err:
            _LOGGER.info(f"could not read sessions data '{type(err).__name__}' -> {err}")

        return json_resp

    async def press_tag(self, tag: Tag, value, idx: str = None) -> dict:
        ret = {}
        if hasattr(tag, "write_type") and tag.write_type is not None:
            final_type = tag.write_type
        else:
            final_type = tag.type

        if final_type == EP_TYPE.LOADPOINTS and idx is not None:
            ret[tag.json_key] = await self.press_loadpoint_key(idx, tag.write_key, value)

        elif final_type == EP_TYPE.VEHICLES:
            # before we can write something to the vehicle endpoints, we must know the vehicle_id!
            # -> so we have to grab from the loadpoint the current vehicle!
            if self._data is not None and len(self._data) > 0 and JSONKEY_LOADPOINTS in self._data:
                try:
                    int_idx = int(idx) - 1
                    vehicle_id = self._data[JSONKEY_LOADPOINTS][int_idx][Tag.LP_VEHICLENAME.json_key]
                    if vehicle_id is not None:
                        ret[tag.json_key] = await self.press_vehicle_key(vehicle_id, tag.write_key, value)

                except Exception as err:
                    _LOGGER.info(f"could not find a connected vehicle at loadpoint: {idx}")

        return ret

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
                r_json = await _do_request(method=self.web_session.patch(url=req, ssl=False))
            else:
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/{write_key}"
                _LOGGER.debug(f"DELETE request: {req}")
                r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False))
        else:
            req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method=self.web_session.post(url=req, ssl=False))

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
                r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False))
            else:
                pass
        else:
            req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method=self.web_session.post(url=req, ssl=False))

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
            r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False))
        else:
            req = f"{self.host}/api/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method=self.web_session.post(url=req, ssl=False))

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def write_loadpoint_key(self, lp_idx_str, write_key, value) -> dict:
        # idx will start with 1!
        if isinstance(value, (bool, int, float)):
            value = str(value).lower()
        elif value is not None:
            value = str(value)

        _LOGGER.info(f"going to write '{value}' for key '{write_key}' to evcc-loadpoint{lp_idx_str}@{self.host}")
        r_json = None
        if value is None:
            req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx_str}/{write_key}"
            _LOGGER.debug(f"DELETE request: {req}")
            r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False))
        else:
            req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx_str}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method=self.web_session.post(url=req, ssl=False))

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
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
        r_json = await _do_request(method=self.web_session.post(url=req, ssl=False))

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
                r_json = await _do_request(method=self.web_session.post(url=req, ssl=False))
            else:
                # DELETE PLAN...
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{idx}/plan/energy"
                _LOGGER.debug(f"DELETE request: {req}")
                r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False))

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
                    r_json = await _do_request(method=self.web_session.post(url=req, ssl=False))
                else:
                    # DELETE PLAN...
                    req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/plan/soc"
                    _LOGGER.debug(f"DELETE request: {req}")
                    r_json = await _do_request(method=self.web_session.delete(url=req, ssl=False))

                if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
                    return r_json
                else:
                    return {"err": "no response from evcc"}

            except Exception as err:
                _LOGGER.error(f"could not write vehicle plan for vehicle: {vehicle_id}, error: {err}")
                return {"err": f"could not write vehicle plan: {err}"}