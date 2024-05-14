import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ID, CONF_HOST, CONF_MODEL, CONF_TYPE, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from custom_components.evcc_intg.pyevcc_ha import EvccApiBridge
from custom_components.evcc_intg.pyevcc_ha.keys import Tag
from .const import (
    DOMAIN, CONF_11KWLIMIT
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class GoeChargerApiV2FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for evcc_intg."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._type = ""
        self._model = ""
        self._serial = ""

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        # Uncomment the next 2 lines if only a single instance of the integration is allowed:
        # if self._async_current_entries():
        #     return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._test_host(host=user_input[CONF_HOST])
            if valid:
                user_input[CONF_MODEL] = self._model.split(' ')[0]
                user_input[CONF_TYPE] = f"{self._type} [{self._model}]"
                user_input[CONF_ID] = self._serial
                user_input[CONF_SCAN_INTERVAL] = max(5, user_input[CONF_SCAN_INTERVAL])
                title = f"go-eCharger API v2 [{self._serial}]"
                return self.async_create_entry(title=title, data=user_input)
            else:
                self._errors["base"] = "auth"
        else:
            user_input = {}
            user_input[CONF_HOST] = ""
            user_input[CONF_SCAN_INTERVAL] = 5

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST)): str,
                vol.Required(CONF_SCAN_INTERVAL, default=user_input.get(CONF_SCAN_INTERVAL)): int,
            }),
            last_step=True,
            errors=self._errors
        )

    async def _test_host(self, host):
        try:
            session = async_create_clientsession(self.hass)
            client = EvccApiBridge(host=host, web_session=session, lang=self.hass.config.language.lower())

            ret = await client.read_system()
            if ret is not None and len(ret) > 0:
                await client.read_versions()
                #self._oem = ret[Tag.OEM.key]
                self._type = str(ret[Tag.TYP.key]).replace('_', ' ')
                self._model = f"{ret[Tag.VAR.key]} kW"
                self._serial = ret[Tag.SSE.key]
                _LOGGER.info(f"successfully validated host -> result: {ret}")
                return True

        except Exception as exc:
            _LOGGER.error(f"Exception while test credentials: {exc}")
        return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GoeChargerApiV2OptionsFlowHandler(config_entry)


class GoeChargerApiV2OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        if len(dict(config_entry.options)) == 0:
            self.options = dict(config_entry.data)
        else:
            self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            user_input[CONF_SCAN_INTERVAL] = max(5, user_input[CONF_SCAN_INTERVAL])
            self.options.update(user_input)
            return await self._update_options()

        # is this the 11kW or the 22kW Version?
        if int(self.options.get(CONF_MODEL)) == 11:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_SCAN_INTERVAL, default=self.options.get(CONF_SCAN_INTERVAL, 5)): int
                })
            )
        else:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_11KWLIMIT, default=self.options.get(CONF_11KWLIMIT, False)): bool,
                    vol.Required(CONF_SCAN_INTERVAL, default=self.options.get(CONF_SCAN_INTERVAL, 5)): int
                })
            )

    async def _update_options(self):
        return self.async_create_entry(title=self.config_entry.title, data=self.options)
