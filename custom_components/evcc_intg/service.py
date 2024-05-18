import datetime
import logging

from homeassistant.core import ServiceCall

_LOGGER: logging.Logger = logging.getLogger(__package__)


class EvccService():
    def __init__(self, hass, config, coordinator):  # pylint: disable=unused-argument
        """Initialize the sensor."""
        self._hass = hass
        self._config = config
        self._coordinator = coordinator

    async def set_loadpoint_plan(self, call: ServiceCall):
        return await self._set_plan(call, False)

    async def set_vehicle_plan(self, call: ServiceCall):
        return await self._set_plan(call, True)

    async def _set_plan(self, call: ServiceCall, write_to_vehicle:bool):
        input_date_str = call.data.get('startdate', None)
        loadpoint = call.data.get('loadpoint', 0)
        if write_to_vehicle:
            set_value = call.data.get('soc', 0)
        else:
            set_value = call.data.get('energy', 0)

        if input_date_str is not None and isinstance(loadpoint, int) and isinstance(set_value, int) and set_value > 0:
            try:
                # date is YYYY-MM-DD HH:MM.SSS -> need to convert it to a UTC based RFC3339
                start = datetime.datetime.strptime(input_date_str, "%Y-%m-%d %H:%M:%S")
                start = start.replace(second=0)
                start = start.astimezone(datetime.timezone.utc)
                start_str = start.isoformat(timespec="milliseconds")
                start_str = start_str.replace("+00:00", "Z")
                resp = await self._coordinator.async_write_plan(write_to_vehicle, str(int(loadpoint)), str(int(set_value)), start_str)
                if resp is not None and len(resp) > 0:
                    if call.return_response:
                        return {
                            "success": "true",
                            "date": str(datetime.datetime.now().time()),
                            "response": resp
                        }
                else:
                    if call.return_response:
                        return {"error": "NO or EMPTY response", "date": str(datetime.datetime.now().time())}
            except ValueError as exc:
                if call.return_response:
                    return {"error": str(exc), "date": str(datetime.datetime.now().time())}

        if call.return_response:
            return {"error": "No date provided (or false data)", "date": str(datetime.datetime.now().time())}
