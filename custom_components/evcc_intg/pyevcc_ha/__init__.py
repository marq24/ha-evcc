import logging
from json import JSONDecodeError
from time import time
from typing import Callable

from aiohttp import ClientResponseError

from custom_components.evcc_intg.pyevcc_ha.const import (
    TRANSLATIONS,
    JSONKEY_LOADPOINTS,
    STATE_QUERY,
    JSONKEY_VEHICLES,
    STATES,
    ADDITIONAL_ENDPOINTS_DATA_TARIFF,
)
from custom_components.evcc_intg.pyevcc_ha.keys import EP_TYPE, Tag, IS_TRIGGER

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def do_request(method: Callable) -> dict:
    async with method as res:
        try:
            if res.status == 200:
                try:
                    return await res.json()

                except JSONDecodeError as json_exc:
                    _LOGGER.warning(f"APP-API: JSONDecodeError while 'await res.json(): {json_exc}")

                except ClientResponseError as io_exc:
                    _LOGGER.warning(f"APP-API: ClientResponseError while 'await res.json(): {io_exc}")

            elif res.status == 500 and int(res.headers['Content-Length']) > 0:
                try:
                    r_json = await res.json()
                    return {"err": r_json}
                except JSONDecodeError as json_exc:
                    _LOGGER.warning(f"APP-API: JSONDecodeError while 'res.status == 500 res.json(): {json_exc}")

                except ClientResponseError as io_exc:
                    _LOGGER.warning(f"APP-API: ClientResponseError while 'res.status == 500 res.json(): {io_exc}")

            else:
                _LOGGER.warning(f"APP-API: write_value failed with http-status {res.status}")

        except ClientResponseError as io_exc:
            _LOGGER.warning(f"APP-API: write_value failed cause: {io_exc}")

    return {}


class EvccApiBridge:
    def __init__(self, host: str, web_session, lang: str = "en") -> None:
        # make sure we are compliant with old configurations (that does not include the schema in the host variable)
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"

        self.host = host
        self.web_session = web_session
        self.lang_map = None
        if lang in TRANSLATIONS:
            self.lang_map = TRANSLATIONS[lang]
        else:
            self.lang_map = TRANSLATIONS["en"]

        self._LAST_FULL_STATE_UPDATE_TS = 0
        self._data = {}

        # by default, we do not request the tariff endpoints
        self.request_tariff_endpoints = False
        self.request_tariff_keys = []

    def enable_tariff_endpoints(self, keys: list):
        self._LAST_FULL_STATE_UPDATE_TS = 0
        self.request_tariff_endpoints = True
        self.request_tariff_keys = keys
        _LOGGER.debug(f"enabled tariff endpoints with keys: {keys}")

    def available_fields(self) -> int:
        return len(self._data)

    def clear_data(self):
        self._LAST_FULL_STATE_UPDATE_TS = 0
        self._data = {}

    async def read_all(self) -> dict:
        # 1 day = 24h * 60min * 60sec = 86400 sec
        # 1 hour = 60min * 60sec = 3600 sec
        # 5 min = 300 sec
        if self._LAST_FULL_STATE_UPDATE_TS + 300 < time():
            await self.read_all_data()
        else:
            new_data = await self.read_frequent_data()
            if new_data is not None:
                for key in STATES:
                    if key in new_data:
                        self._data[key] = new_data[key]
                    else:
                        _LOGGER.info(f"missing '{key}' in response {new_data}")

        return self._data

    async def read_all_data(self) -> dict:
        _LOGGER.info(f"going to read all data from evcc@{self.host}")
        req = f"{self.host}/api/state"
        _LOGGER.debug(f"GET request: {req}")
        json_resp = await do_request(method = self.web_session.get(url=req, ssl=False))
        if len(json_resp) is not None:
            self._LAST_FULL_STATE_UPDATE_TS = time()

        if "result" in json_resp:
            json_resp = json_resp["result"]

        self._data = json_resp
        if self.request_tariff_endpoints:
            json_resp = await self.read_tariff_data(json_resp)
        return json_resp

    async def read_frequent_data(self) -> dict:
        # make sure that idx is really an int...
        _LOGGER.info(f"going to read all frequent_data from evcc@{self.host}")
        req = f"{self.host}/api/state{STATE_QUERY}"
        _LOGGER.debug(f"GET request: {req}")
        return await do_request(method = self.web_session.get(url=req, ssl=False))

    async def read_tariff_data(self, json_resp: dict) -> dict:
        #_LOGGER.info(f"going to request additional tariff data from evcc@{self.host}")
        if ADDITIONAL_ENDPOINTS_DATA_TARIFF not in json_resp:
            json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF] = {}

        for a_key in self.request_tariff_keys:
            try:
                req = f"{self.host}/api/{EP_TYPE.TARIFF.value}/{a_key}"
                _LOGGER.debug(f"GET request: {req}")
                tariff_resp = await do_request(method = self.web_session.get(url=req, ssl=False))
                if "result" in tariff_resp:
                    json_resp[ADDITIONAL_ENDPOINTS_DATA_TARIFF][a_key] = tariff_resp["result"]
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
                r_json = await do_request(method = self.web_session.patch(url=req, ssl=False))
            else:
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/{write_key}"
                _LOGGER.debug(f"DELETE request: {req}")
                r_json = await do_request(method = self.web_session.delete(url=req, ssl=False))
        else:
            req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await do_request(method = self.web_session.post(url=req, ssl=False))

        if r_json is not None and len(r_json) > 0:
            if "result" in r_json:
                self._LAST_FULL_STATE_UPDATE_TS = 0
                return r_json["result"]
            else:
                return {"err": r_json}

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
                r_json = await do_request(method = self.web_session.delete(url=req, ssl=False))
            else:
                pass
        else:
            req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await do_request(method = self.web_session.post(url=req, ssl=False))

        if r_json is not None and len(r_json) > 0:
            if "result" in r_json:
                self._LAST_FULL_STATE_UPDATE_TS = 0
                ret = r_json["result"]
                if len(ret) == 0:
                    ret[write_key] = "OK"
                return ret
            else:
                return {"err": r_json}

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
            r_json = await do_request(method = self.web_session.delete(url=req, ssl=False))
        else:
            req = f"{self.host}/api/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await do_request(method = self.web_session.post(url=req, ssl=False))

        if r_json is not None and len(r_json) > 0:
            if "result" in r_json:
                self._LAST_FULL_STATE_UPDATE_TS = 0
                return r_json["result"]
            else:
                return {"err": r_json}

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
            r_json = await do_request(method = self.web_session.delete(url=req, ssl=False))
        else:
            req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{lp_idx_str}/{write_key}/{value}"
            _LOGGER.debug(f"POST request: {req}")
            r_json = await do_request(method = self.web_session.post(url=req, ssl=False))

        if r_json is not None and len(r_json) > 0:
            if "result" in r_json:
                self._LAST_FULL_STATE_UPDATE_TS = 0
                return r_json["result"]
            else:
                return {"err": r_json}

    async def write_vehicle_key(self, vehicle_id:str, write_key, value) -> dict:
        if isinstance(value, (bool, int, float)):
            value = str(value).lower()
        else:
            value = str(value)

        _LOGGER.info(f"going to write '{value}' for key '{write_key}' to evcc-vehicle{vehicle_id}@{self.host}")
        req = f"{self.host}/api/{EP_TYPE.VEHICLES.value}/{vehicle_id}/{write_key}/{value}"
        _LOGGER.debug(f"POST request: {req}")
        r_json = await do_request(method = self.web_session.post(url=req, ssl=False))

        if r_json is not None and len(r_json) > 0:
            if "result" in r_json:
                self._LAST_FULL_STATE_UPDATE_TS = 0
                return r_json["result"]
            else:
                return {"err": r_json}

    async def write_loadpoint_plan(self, idx:str, energy:str, rfc_date:str):
        # before we can write something to the vehicle endpoints, we must know the vehicle_id!
        # -> so we have to grab from the loadpoint the current vehicle!
            try:
                req = f"{self.host}/api/{EP_TYPE.LOADPOINTS.value}/{idx}/plan/energy/{energy}/{rfc_date}"
                _LOGGER.debug(f"POST request: {req}")
                r_json = await do_request(method = self.web_session.post(url=req, ssl=False))
                if r_json is not None and len(r_json) > 0:
                    if "result" in r_json:
                        self._LAST_FULL_STATE_UPDATE_TS = 0
                        return r_json["result"]
                    else:
                        return {"err": r_json}

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
                    r_json = await do_request(method = self.web_session.post(url=req, ssl=False))
                    if r_json is not None and len(r_json) > 0:
                        if "result" in r_json:
                            self._LAST_FULL_STATE_UPDATE_TS = 0
                            return r_json["result"]
                        else:
                            return {"err": r_json}

            except Exception as err:
                _LOGGER.info(f"could not find a connected vehicle at loadpoint: {idx}")
