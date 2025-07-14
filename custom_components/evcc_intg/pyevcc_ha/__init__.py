import asyncio
import logging
from datetime import datetime, timezone
from json import JSONDecodeError
from numbers import Number
from typing import Callable

import aiohttp
from aiohttp import ClientResponseError, ClientConnectorError, ClientError

from custom_components.evcc_intg.pyevcc_ha.const import (
    TRANSLATIONS,
    JSONKEY_LOADPOINTS,
    JSONKEY_VEHICLES,
    ADDITIONAL_ENDPOINTS_DATA_TARIFF,
)
from custom_components.evcc_intg.pyevcc_ha.keys import EP_TYPE, Tag, IS_TRIGGER
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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

                elif int(res.headers['Content-Length']) > 0:
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
                _LOGGER.warning(f"_do_request() failed cause: {type(ex)} - {ex} [caused by {res.request_info.method} {res.request_info.url}]")
            return {}

    except ClientError as exception:
        _LOGGER.warning(f"_do_request() cause of ClientConnectorError: {exception}")
    except Exception as other:
        _LOGGER.warning(f"_do_request() unexpected: {type(other)} - {other}")


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

        self._LAST_UPDATE_HOUR = -1
        self._data = {}

        # by default, we do not request the tariff endpoints
        self.request_tariff_endpoints = False
        self.request_tariff_keys = []

    def enable_tariff_endpoints(self, keys: list):
        self._LAST_UPDATE_HOUR = -1
        self.request_tariff_endpoints = True
        self.request_tariff_keys = keys
        _LOGGER.debug(f"enabled tariff endpoints with keys: {keys}")

    def available_fields(self) -> int:
        return len(self._data)

    def clear_data(self):
        self._LAST_UPDATE_HOUR = -1
        self._data = {}

    def tariffs_need_update(self) -> bool:
        if self.request_tariff_endpoints and self._LAST_UPDATE_HOUR != datetime.now(timezone.utc).hour:
            return True
        else:
            return False

    async def ws_update_tariffs_if_required(self):
        """if we are in websocket mode, then we must (at least once each hour) update the tariff-data - we call
        this method in the watchdog to make sure that we have the latest data available!
        """
        if self.tariffs_need_update():
            await self.read_all_data(request_only_tariffs=True)

    async def connect_ws(self):
        try:
            async with self.web_session.ws_connect(self.web_socket_url) as ws:
                self.ws_connected = True
                _LOGGER.info(f"connected to websocket: {self.web_socket_url}")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            if self._data is None or len(self._data) == 0:
                                self._LAST_UPDATE_HOUR = -1
                                await self.read_all_data(request_only_tariffs=False)
                        except:
                            _LOGGER.info(f"could not read initial data from evcc@{self.host} - ignoring")
                            self._data = {}

                        try:
                            ws_data = msg.json()
                            for key, value in ws_data.items():
                                if "." in key:
                                    key_parts = key.split(".")
                                    if len(key_parts) > 2:
                                        domain = key_parts[0]
                                        idx = int(key_parts[1])
                                        sub_key = key_parts[2]
                                        if domain in self._data:
                                            if len(self._data[domain]) > idx:
                                                if sub_key in self._data[domain][idx]:
                                                    self._data[domain][idx][sub_key] = value
                                                else:
                                                    self._data[domain][idx][sub_key] = value
                                                    _LOGGER.debug(f"adding '{sub_key}' to {domain}[{idx}]")
                                            else:
                                                # we need to add a new entry to the list... - well
                                                # if we get index 4 but length is only 2 we must add multiple
                                                # empty entries to the list...
                                                while(len(self._data[domain]) <= idx):
                                                    self._data[domain].append({})
                                                self._data[domain][idx] = {sub_key: value}
                                                _LOGGER.debug(f"adding index {idx} to '{domain}' -> {self._data[domain][idx]}")
                                        else:
                                            _LOGGER.info(f"unhandled [{domain} not in data] {key} - ignoring: {value} data: {self._data}")
                                        # if domain == "loadpoints":
                                        #     pass
                                        # elif domain == "vehicles":
                                        #     pass
                                    else:
                                        _LOGGER.info(f"unhandled [not parsable key] {key} - ignoring: {value}")
                                else:
                                    if key in self._data:
                                        self._data[key] = value
                                    else:
                                        if key != "releaseNotes":
                                            self._data[key] = value
                                            _LOGGER.info(f"'added {key}' to self._data and assign: {value}")

                            #END of for loop
                            #_LOGGER.debug(f"key: {key} value: {value}")
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
        except ClientConnectorError as con:
            _LOGGER.error(f"Could not connect to websocket: {con}")
        except BaseException as ex:
            _LOGGER.error(f"BaseException@websocket: {type(ex)} {ex}")

        self.ws_connected = False

    async def _debounce_coordinator_update(self):
        await asyncio.sleep(0.3)
        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(self._data)

    async def read_all_data(self, request_only_tariffs : bool = False) -> dict:
        if request_only_tariffs:
            if self._data is None:
                self._data = {}
            json_resp = self._data
        else:
            _LOGGER.debug(f"going to read all data from evcc@{self.host}")
            req = f"{self.host}/api/state"
            _LOGGER.debug(f"GET request: {req}")
            json_resp = await _do_request(method = self.web_session.get(url=req, ssl=False))
            if json_resp is not None and len(json_resp) == 0:
                _LOGGER.info(f"could not read data from evcc@{self.host} - using empty data")

        if self.request_tariff_endpoints:
            _LOGGER.debug(f"going to request tariff data from evcc@{self.host}")
            # we only update the tariff data once per hour...
            current_hour = datetime.now(timezone.utc).hour
            if self._LAST_UPDATE_HOUR != current_hour:
                json_resp = await self.read_tariff_data(json_resp)
                self._LAST_UPDATE_HOUR = current_hour
            else:
                # we must copy the previous existing data to the new json_resp!
                if ADDITIONAL_ENDPOINTS_DATA_TARIFF in self._data:
                    json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF] = self._data[ADDITIONAL_ENDPOINTS_DATA_TARIFF]

        self._data = json_resp
        return json_resp

    async def read_tariff_data(self, json_resp: dict) -> dict:
        #_LOGGER.info(f"going to request additional tariff data from evcc@{self.host}")
        if ADDITIONAL_ENDPOINTS_DATA_TARIFF not in json_resp:
            json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF] = {}

        for a_key in self.request_tariff_keys:
            try:
                req = f"{self.host}/api/{EP_TYPE.TARIFF.value}/{a_key}"
                _LOGGER.debug(f"GET request: {req}")
                tariff_resp = await _do_request(method = self.web_session.get(url=req, ssl=False))
                if tariff_resp is not None and len(tariff_resp) > 0:
                    json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF][a_key] = tariff_resp
            except Exception as err:
                _LOGGER.info(f"could not read tariff data for '{a_key}' -> '{err}'")

        return json_resp

    async def press_tag(self, tag: Tag, value, idx:str = None) -> dict:
        ret = {}
        if hasattr(tag, "write_type") and tag.write_type is not None:
            final_type = tag.write_type
        else:
            final_type = tag.type

        if final_type == EP_TYPE.LOADPOINTS and idx is not None:
            ret[tag.key] = await self.press_loadpoint_key(idx, tag.write_key, value)

        elif final_type == EP_TYPE.VEHICLES:
            # before we can write something to the vehicle endpoints, we must know the vehicle_id!
            # -> so we have to grab from the loadpoint the current vehicle!
            if len(self._data) > 0 and JSONKEY_LOADPOINTS in self._data:
                try:
                    int_idx = int(idx) - 1
                    vehicle_id = self._data[JSONKEY_LOADPOINTS][int_idx][Tag.VEHICLENAME.key]
                    if vehicle_id is not None:
                        ret[tag.key] = await self.press_vehicle_key(vehicle_id, tag.write_key, value)

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
            if write_key == Tag.DETECTVEHICLE.write_key:
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/vehicle"
                _LOGGER.debug(f"PATCH request: {req}")
                r_json = await _do_request(method = self.web_session.patch(url=req, ssl=False))
            else:
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/{write_key}"
                _LOGGER.debug(f"DELETE request: {req}")
                r_json = await _do_request(method = self.web_session.delete(url=req, ssl=False))
        else:
            req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method = self.web_session.post(url=req, ssl=False))

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def press_vehicle_key(self, vehicle_id:str, write_key, value) -> dict:
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
                r_json = await _do_request(method = self.web_session.delete(url=req, ssl=False))
            else:
                pass
        else:
            req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method = self.web_session.post(url=req, ssl=False))

        if r_json is not None:
            if (hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str)):
                r_json[write_key] = "OK"
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def write_tag(self, tag: Tag, value, idx_str:str = None) -> dict:
        ret = {}
        if hasattr(tag, "write_type") and tag.write_type is not None:
            final_type = tag.write_type
        else:
            final_type = tag.type

        if final_type == EP_TYPE.SITE:
            ret[tag.key] = await self.write_site_key(tag.write_key, value)

        elif final_type == EP_TYPE.LOADPOINTS and idx_str is not None:
            ret[tag.key] = await self.write_loadpoint_key(idx_str, tag.write_key, value)

        elif final_type == EP_TYPE.VEHICLES:
            # before we can write something to the vehicle endpoints, we must know the vehicle_id!
            # -> so we have to grab from the loadpoint the current vehicle!
            if len(self._data) > 0 and JSONKEY_LOADPOINTS in self._data:
                try:
                    int_idx = int(idx_str) - 1
                    vehicle_id = self._data[JSONKEY_LOADPOINTS][int_idx][Tag.VEHICLENAME.key]
                    if vehicle_id is not None:
                        ret[tag.key] = await self.write_vehicle_key(vehicle_id, tag.write_key, value)

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
            r_json = await _do_request(method = self.web_session.delete(url=req, ssl=False))
        else:
            req = f"{self.host}/api/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method = self.web_session.post(url=req, ssl=False))

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
            r_json = await _do_request(method = self.web_session.delete(url=req, ssl=False))
        else:
            req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx_str}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await _do_request(method = self.web_session.post(url=req, ssl=False))

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def write_vehicle_key(self, vehicle_id:str, write_key, value) -> dict:
        if isinstance(value, (bool, int, float)):
            value = str(value).lower()
        else:
            value = str(value)

        _LOGGER.info(f"going to write '{value}' for key '{write_key}' to evcc-vehicle{vehicle_id}@{self.host}")
        req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/{write_key}/{value}"
        _LOGGER.debug(f"POST request: {req}")
        r_json = await _do_request(method = self.web_session.post(url=req, ssl=False))

        if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
            return r_json
        else:
            return {"err": "no response from evcc"}

    async def write_loadpoint_plan(self, idx:str, energy:str, rfc_date:str):
        # before we can write something to the vehicle endpoints, we must know the vehicle_id!
        # -> so we have to grab from the loadpoint the current vehicle!
            try:
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{idx}/plan/energy/{energy}/{rfc_date}"
                _LOGGER.debug(f"POST request: {req}")
                r_json = await _do_request(method = self.web_session.post(url=req, ssl=False))
                if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
                    return r_json
                else:
                    return {"err": "no response from evcc"}

            except Exception as err:
                _LOGGER.info(f"could not write to loadpoint: {idx}")

    async def write_vehicle_plan_for_loadpoint_index(self, idx:str, soc:str, rfc_date:str):
        # before we can write something to the vehicle endpoints, we must know the vehicle_id!
        # -> so we have to grab from the loadpoint the current vehicle!
        if len(self._data) > 0 and JSONKEY_LOADPOINTS in self._data:
            try:
                int_idx = int(idx) - 1
                vehicle_id = self._data[JSONKEY_LOADPOINTS][int_idx][Tag.VEHICLENAME.key]
                if vehicle_id is not None:
                    req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/plan/soc/{soc}/{rfc_date}"
                    _LOGGER.debug(f"POST request: {req}")
                    r_json = await _do_request(method = self.web_session.post(url=req, ssl=False))
                    if r_json is not None and ((hasattr(r_json, "len") and len(r_json) > 0) or isinstance(r_json, (Number, str))):
                        return r_json
                    else:
                        return {"err": "no response from evcc"}

            except Exception as err:
                _LOGGER.info(f"could not find a connected vehicle at loadpoint: {idx}")