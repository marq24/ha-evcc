import asyncio
import datetime
import logging

from homeassistant.core import ServiceCall

from custom_components.evcc_intg.pyevcc_ha.keys import Tag

_LOGGER: logging.Logger = logging.getLogger(__package__)


class EvccService():
    def __init__(self, hass, config, coordinator):  # pylint: disable=unused-argument
        """Initialize the sensor."""
        self._hass = hass
        self._config = config
        self._coordinator = coordinator
        self._stop_in_progress = False

    async def set_pv_data(self, call: ServiceCall):
        pgrid = call.data.get('pgrid', None)
        ppv = call.data.get('ppv', 0)
        pakku = call.data.get('pakku', 0)
        if pgrid is not None and isinstance(pgrid, (int, float)):
            if not isinstance(ppv, (int, float)):
                ppv = 0
            if not isinstance(pakku, (int, float)):
                pakku = 0

            payload = {
                "pGrid": float(pgrid),
                "pPv": float(ppv),
                "pAkku": float(pakku)
            }
            _LOGGER.debug(f"Service set PV data: {payload}")
            try:
                resp = await self._coordinator.async_write_key(Tag.IDS.key, payload)
                if call.return_response:
                    return {
                        "success": "true",
                        "date": str(datetime.datetime.now().time()),
                        "response": resp
                    }

            except ValueError as exc:
                if call.return_response:
                    return {"error": str(exc), "date": str(datetime.datetime.now().time())}

        if call.return_response:
            return {"error": "No Grid Power provided (or false data)", "date": str(datetime.datetime.now().time())}

    async def stop_charging(self, call: ServiceCall):
        if not self._stop_in_progress:
            self._stop_in_progress = True
            _LOGGER.debug(f"Force STOP_CHARGING")

            try:
                resp = await self._coordinator.async_write_key(Tag.FRC.key, 1)
                if Tag.FRC.key in resp:
                    _LOGGER.debug(f"STOP_CHARGING: waiting for 5 minutes...")
                    await asyncio.sleep(300)
                    _LOGGER.debug(f"STOP_CHARGING: 5 minutes are over... disable charging LOCK again")

                    resp = await self._coordinator.async_write_key(Tag.FRC.key, 0)

                    self._stop_in_progress = False
                    if call.return_response:
                        return {
                            "success": "true",
                            "date": str(datetime.datetime.now().time()),
                            "response": resp
                        }

                else:
                    _LOGGER.debug(f"response does not contain {Tag.FRC.key}: {resp}")

                    self._stop_in_progress = False
                    if call.return_response:
                        return {"error": "A STOP_CHARGING request could not be send", "date": str(datetime.datetime.now().time())}

            except ValueError as exc:
                if call.return_response:
                    return {"error": str(exc), "date": str(datetime.datetime.now().time())}

        else:
            if call.return_response:
                return {"error": "A STOP_CHARGING request is already in progress", "date": str(datetime.datetime.now().time())}
