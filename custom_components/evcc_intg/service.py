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

    def get_available_vehicles_from_entities(self):
        """Get list of available vehicle names from select.evcc_*_vehicle_name entities."""
        vehicle_names = []

        try:
            # Get all states from Home Assistant
            states = self._hass.states.async_all()

            # Find all select.evcc_*_vehicle_name entities
            for state in states:
                entity_id = state.entity_id
                if (entity_id.startswith("select.evcc_") and
                    entity_id.endswith("_vehicle_name") and
                    state.state and
                    state.state not in ["unavailable", "unknown", ""]):

                    vehicle_names.append(state.state)
                    _LOGGER.debug(f"Found vehicle from {entity_id}: {state.state}")

            # Remove duplicates and sort
            unique_vehicles = sorted(list(set(vehicle_names)))
            _LOGGER.debug(f"Available vehicles from entities: {unique_vehicles}")
            return unique_vehicles

        except Exception as e:
            _LOGGER.debug(f"Could not get vehicle names from entities: {e}")
            return self.get_available_vehicles_fallback()

    def get_available_vehicles_fallback(self):
        """Fallback method to get vehicle names from coordinator data."""
        vehicle_names = []

        try:
            # Get vehicle names from coordinator data
            if hasattr(self._coordinator, 'data') and self._coordinator.data:
                # Look for vehicles in the evcc data structure
                data = self._coordinator.data
                if 'vehicles' in data:
                    for vehicle in data['vehicles']:
                        if 'name' in vehicle:
                            vehicle_names.append(vehicle['name'])
                        elif 'title' in vehicle:
                            vehicle_names.append(vehicle['title'])

                # Also check loadpoints for connected vehicles
                if 'loadpoints' in data:
                    for lp in data['loadpoints']:
                        if 'vehicleName' in lp and lp['vehicleName']:
                            vehicle_names.append(lp['vehicleName'])

            # Remove duplicates and sort
            return sorted(list(set([v for v in vehicle_names if v and v != ""])))

        except Exception as e:
            _LOGGER.debug(f"Could not get vehicle names: {e}")
            return ["vehicle_1"]  # Final fallback

    async def set_loadpoint_plan(self, call: ServiceCall):
        return await self._set_plan(call, False)

    async def set_vehicle_plan(self, call: ServiceCall):
        """Set vehicle plan directly by vehicle name/id - no loadpoint needed."""
        return await self._set_vehicle_plan_direct(call)

    async def _set_vehicle_plan_direct(self, call: ServiceCall):
        """Set vehicle plan directly by vehicle name/id."""
        input_date_str = call.data.get("startdate", None)
        vehicle_name = call.data.get("vehicle", None)
        soc = call.data.get("soc", 0)
        precondition = call.data.get("precondition", None)

        # Get available vehicles for better error messages
        available_vehicles = self.get_available_vehicles_from_entities()
        _LOGGER.debug(f"Available vehicles: {available_vehicles}")

        if input_date_str is not None and vehicle_name and isinstance(soc, int) and soc > 0:
            try:
                # date is YYYY-MM-DD HH:MM.SSS -> need to convert it to a UTC based RFC3339
                start = datetime.datetime.strptime(input_date_str, "%Y-%m-%d %H:%M:%S")
                start = start.replace(second=0)
                start = start.astimezone(datetime.timezone.utc)
                start_str = start.isoformat(timespec="milliseconds")
                start_str = start_str.replace("+00:00", "Z")

                resp = await self._coordinator.async_write_vehicle_plan_direct(vehicle_name, str(int(soc)), start_str, precondition)
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

        if call.return_response:
            return {
                "error": "No date, vehicle name, or false data provided",
                "date": str(datetime.datetime.now().time())
            }

    async def _set_plan(self, call: ServiceCall, write_to_vehicle: bool):
        input_date_str = call.data.get("startdate", None)
        loadpoint = call.data.get("loadpoint", 0)

        # SOC or ENERGY depending on from Mode
        if write_to_vehicle:
            set_value = call.data.get("soc", 0)
        else:
            set_value = call.data.get("energy", 0)

        precondition = call.data.get("precondition", None)

        if input_date_str is not None and isinstance(loadpoint, int) and isinstance(set_value, int) and set_value > 0:
            try:
                # date is YYYY-MM-DD HH:MM.SSS -> need to convert it to a UTC based RFC3339
                start = datetime.datetime.strptime(input_date_str, "%Y-%m-%d %H:%M:%S")
                start = start.replace(second=0)
                start = start.astimezone(datetime.timezone.utc)
                start_str = start.isoformat(timespec="milliseconds")
                start_str = start_str.replace("+00:00", "Z")
                resp = await self._coordinator.async_write_plan(write_to_vehicle, str(int(loadpoint)), str(int(set_value)), start_str, precondition)
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

        if call.return_response:
            return {
                "error": "No date provided (or false data)",
                "date": str(datetime.datetime.now().time())
            }
