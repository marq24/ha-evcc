import datetime
import logging

from homeassistant.core import ServiceCall

_LOGGER: logging.Logger = logging.getLogger(__package__)


class EvccService:
    def __init__(self, hass, config, coordinator):  # pylint: disable=unused-argument
        """Initialize the sensor."""
        self._hass = hass
        self._config = config
        self._coordinator = coordinator

    async def set_loadpoint_plan(self, call: ServiceCall):
        return await self.set_plan(call)

    async def set_vehicle_plan(self, call: ServiceCall):
        """Set vehicle plan directly by vehicle name/id."""
        return await self.set_plan(call)

    async def set_plan(self, call: ServiceCall):
        # common for both...
        input_date_str = call.data.get("startdate", None)

        # vehicle plan data
        vehicle_name = call.data.get("vehicle", None)
        soc = call.data.get("soc", None)
        precondition = call.data.get("precondition", None)

        # loadpoint plan data
        loadpoint = call.data.get("loadpoint", None)
        energy = call.data.get("energy", None)

        if vehicle_name:
            # Get available vehicles...
            available_vehicles = list(self._coordinator._vehicle.keys())
            _LOGGER.debug(f"Available vehicles: {available_vehicles}")
        else:
            available_vehicles = []

        # Validate input
        if input_date_str is not None:
            try:
                # date is YYYY-MM-DD HH:MM.SSS -> need to convert it to a UTC based RFC3339
                start = datetime.datetime.strptime(input_date_str, "%Y-%m-%d %H:%M:%S")
                start = start.replace(second=0)
                start = start.astimezone(datetime.timezone.utc)
                rfc_date = start.isoformat(timespec="milliseconds").replace("+00:00", "Z")

                # Vehicle plan
                if vehicle_name is not None and vehicle_name in available_vehicles and isinstance(soc, int) and soc > 0:
                    resp = await self._coordinator.async_write_plan(vehicle_name, None, str(int(soc)), rfc_date, precondition)

                # Loadpoint plan
                elif loadpoint is not None and isinstance(loadpoint, int) and isinstance(energy, int) and energy > 0:
                    resp = await self._coordinator.async_write_plan(None, str(int(loadpoint)), str(int(energy)), rfc_date, None)

                else:
                    resp = None

                if resp is not None and len(resp) > 0:
                    if call.return_response:
                        return {
                            "success": "true",
                            "date": str(datetime.datetime.now().time()),
                            "response": resp
                        }
                else:
                    if call.return_response:
                        return {
                            "error": "NO or EMPTY response",
                            "date": str(datetime.datetime.now().time())
                        }
            except ValueError as exc:
                if call.return_response:
                    return {
                        "error": str(exc),
                        "date": str(datetime.datetime.now().time())
                    }
        else:
            if call.return_response:
                return {
                    "error": "No date or false data provided",
                    "date": str(datetime.datetime.now().time())
                }


    async def del_loadpoint_plan(self, call: ServiceCall):
        return await self.del_plan(call)

    async def del_vehicle_plan(self, call: ServiceCall):
        return await self.del_plan(call)

    async def del_plan(self, call: ServiceCall):
        # vehicle plan data
        vehicle_name = call.data.get("vehicle", None)

        # loadpoint plan data
        loadpoint = call.data.get("loadpoint", None)

        if vehicle_name:
            # Get available vehicles...
            available_vehicles = list(self._coordinator._vehicle.keys())
            _LOGGER.debug(f"Available vehicles: {available_vehicles}")
        else:
            available_vehicles = []

        # Validate input
        if vehicle_name is not None or loadpoint is not None:
            try:

                # Vehicle plan
                if vehicle_name is not None and vehicle_name in available_vehicles:
                    resp = await self._coordinator.async_delete_plan(vehicle_name, None)

                # Loadpoint plan
                elif loadpoint is not None and isinstance(loadpoint, int):
                    resp = await self._coordinator.async_delete_plan(None, str(int(loadpoint)))

                else:
                    resp = None

                if resp is not None and len(resp) > 0:
                    if call.return_response:
                        return {
                            "success": "true",
                            "date": str(datetime.datetime.now().time()),
                            "response": resp
                        }
                else:
                    if call.return_response:
                        return {
                            "error": "NO or EMPTY response",
                            "date": str(datetime.datetime.now().time())
                        }
            except ValueError as exc:
                if call.return_response:
                    return {
                        "error": str(exc),
                        "date": str(datetime.datetime.now().time())
                    }
        else:
            if call.return_response:
                return {
                    "error": "No date or false data provided",
                    "date": str(datetime.datetime.now().time())
                }
