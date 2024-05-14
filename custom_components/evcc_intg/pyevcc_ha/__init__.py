import json
import logging
from json import JSONDecodeError
from time import time
from typing import Callable

from aiohttp import ClientResponseError

from custom_components.evcc_intg.pyevcc_ha.const import (
    TRANSLATIONS,
    FILTER_LOADPOINTS, FILTER_ALL_CONFIG, CAR_VALUES, FILTER_MIN_STATES, FILTER_TIMES_ADDON, FILTER_ALL_STATES,
)
from custom_components.evcc_intg.pyevcc_ha.keys import ENDPOINT_TYPE, Tag, IS_TRIGGER, ApiKey

_LOGGER: logging.Logger = logging.getLogger(__package__)


class EvccApiBridge:
    def __init__(self, host: str, web_session, lang: str = "en") -> None:
        self.host = host
        self.web_session = web_session
        self.lang_map = None
        if lang in TRANSLATIONS:
            self.lang_map = TRANSLATIONS[lang]
        else:
            self.lang_map = TRANSLATIONS["en"]

        self._LAST_CONFIG_UPDATE_TS = 0
        self._LAST_FULL_STATE_UPDATE_TS = 0
        self._versions = {}
        self._states = {}
        self._config = {}

    def available_fields(self) -> int:
        return len(self._versions) + len(self._states) + len(self._config)

    def clear_data(self):
        self._LAST_CONFIG_UPDATE_TS = 0
        self._LAST_FULL_STATE_UPDATE_TS = 0
        self._versions = {}
        self._states = {}
        self._config = {}

    async def read_all(self) -> dict:
        await self.read_all_states();
        # 1 day = 24h * 60min * 60sec = 86400 sec
        # 1 hour = 60min * 60sec = 3600 sec
        if self._LAST_CONFIG_UPDATE_TS + 3600 < time():
            await self.read_all_config();

        return self._versions | self._states | self._config

    async def read_all_states(self):
        # ok we are in idle state - so we do not need all states... [but 5 minutes (=300sec) do a full update]
        if "car" in self._states and CAR_VALUES.IDLE.value == self._states["car"] and self._LAST_FULL_STATE_UPDATE_TS + 300 > time():
            filter = FILTER_MIN_STATES

            # check waht additional times do frequent upddate?!
            filter = filter+FILTER_TIMES_ADDON

            idle_states = await self._read_filtered_data(filters=filter, log_info="read_idle_states")
            if len(idle_states) > 0:
                # copy all fields from 'idle_states' to self._states
                self._states.update(idle_states)

                # chck, if the car idle state have changed to something else
                if Tag.CAR.key in self._states and self._states[Tag.CAR.key] != CAR_VALUES.IDLE.value:
                    # the car state is not 'idle' - so we should fetch all states...
                    await self.read_all_states()

        else:
            self._states = await self._read_filtered_data(filters=FILTER_ALL_STATES, log_info="read_all_states")
            if len(self._states) > 0:
                self._LAST_FULL_STATE_UPDATE_TS = time()

    async def force_config_update(self):
        self._LAST_CONFIG_UPDATE_TS = 0
        await self.read_all_config()

    async def read_all_config(self):
        self._config = await self._read_filtered_data(filters=FILTER_ALL_CONFIG, log_info="read_all_config")
        if len(self._config) > 0:
            self._LAST_CONFIG_UPDATE_TS = time()

    async def _read_filtered_data(self, filters: str, log_info: str) -> dict:
        args = {"filter": filters}
        req_field_count = len(args['filter'].split(','))
        _LOGGER.debug(f"going to request {req_field_count} keys from go-eCharger@{self.host}")
        async with self.web_session.get(f"http://{self.host}/api/status", params=args) as res:
            try:
                res.raise_for_status()
                if res.status == 200:
                    try:
                        r_json = await res.json()
                        if r_json is not None and len(r_json) > 0:
                            resp_field_count = len(r_json)
                            if resp_field_count >= req_field_count:
                                _LOGGER.debug(f"read {resp_field_count} values from go-eCharger@{self.host}")
                            else:
                                missing_fields_in_reponse = []
                                requested_fields = args['filter'].split(',')
                                for a_req_key in requested_fields:
                                    if a_req_key not in r_json:
                                        missing_fields_in_reponse.append(a_req_key)

                                _LOGGER.info(
                                    f"[missing fields: {len(missing_fields_in_reponse)} -> {missing_fields_in_reponse}] - not all requested fields where present in the response from from go-eCharger@{self.host}")
                            return r_json

                    except JSONDecodeError as json_exc:
                        _LOGGER.warning(f"APP-API: JSONDecodeError while 'await res.json(): {json_exc}")

                    except ClientResponseError as io_exc:
                        _LOGGER.warning(f"APP-API: ClientResponseError while 'await res.json(): {io_exc}")

                else:
                    _LOGGER.warning(f"APP-API: {log_info} failed with http-status {res.status}")

            except ClientResponseError as io_exc:
                _LOGGER.warning(f"APP-API: {log_info} failed cause: {io_exc}")

        return {}

    async def _read_all_data(self) -> dict:
        _LOGGER.info(f"going to read all data from evcc@{self.host}")
        json_resp = await self.do_request(method = self.web_session.get(f"http://{self.host}/api/state"))
        if len(json_resp) is not None:
            _LAST_FULL_STATE_UPDATE_TS = time()
        return json_resp

    async def read_tag(self, idx, tag: ApiKey) -> dict:
        if tag.type == ENDPOINT_TYPE.LOADPOINT:
            return await self.read_loadpoint_key(idx, tag.key)

    async def read_loadpoint_key(self, idx, read_key) -> dict:
        # make sure that idx is really an int...
        idx = int(idx)
        _LOGGER.info(f"going to read key '{read_key}' from evcc-loadpoint{idx}@{self.host}")
        r_json = await self.do_request(method = self.web_session.get(f"http://{self.host}/api/state"+FILTER_LOADPOINTS))
        if r_json is not None and len(r_json) >= idx:
            if read_key in r_json[idx-1]:
                return r_json[idx-1][read_key]

    async def read_loadpoint(self, idx) -> dict:
        # make sure that idx is really an int...
        idx = int(idx)
        _LOGGER.info(f"going to read loadpoint at index '{idx}' from evcc-loadpoint{idx}@{self.host}")
        r_json = await self.do_request(method = self.web_session.get(f"http://{self.host}/api/state"+FILTER_LOADPOINTS))
        if r_json is not None and len(r_json) >= idx:
            return r_json[idx-1]

    async def read_loadpoints(self) -> dict:
        # make sure that idx is really an int...
        _LOGGER.info(f"going to read all loadpoints from evcc-loadpoints@{self.host}")
        return await self.do_request(method = self.web_session.get(f"http://{self.host}/api/state"+FILTER_LOADPOINTS))

    async def write_tag(self, idx, tag: ApiKey, value) -> dict:
        if tag.type == ENDPOINT_TYPE.LOADPOINT:
            await self.write_loadpoint_key(idx, tag.write_key, value)

    async def write_loadpoint_key(self, idx, write_key, value) -> dict:
        # idx will start with 1!

        if isinstance(value, (bool, int, float)):
            value = str(value).lower()
        #elif isinstance(value, dict):
        #    args = {key: json.dumps(value)}
        #elif isinstance(value, str) and value == IS_TRIGGER:
        #    # ok this are special trigger actions, that we want to call from the FE...
        #    match key:
        #        case Tag.INTERNAL_FORCE_CONFIG_READ.key:
        #            await self.force_config_update()
        #    return {key: value}
        else:
            value = str(value)

        _LOGGER.info(f"going to write '{value}' for key '{write_key}' to evcc-loadpoint{idx}@{self.host}")
        r_json = await self.do_request(
            method = self.web_session.post(f"http://{self.host}/api/loadpoints/{idx}/{write_key}/{value}"),
        )

        if r_json is not None and len(r_json) > 0:
            if write_key in r_json and r_json[write_key]:
                self._LAST_CONFIG_UPDATE_TS = 0
                self._LAST_FULL_STATE_UPDATE_TS = 0
                return {write_key: value}
            else:
                return {"err": r_json}

    async def do_request(self, method: Callable) -> dict:
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
