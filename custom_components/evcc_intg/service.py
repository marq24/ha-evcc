import datetime
import zoneinfo
import logging

from homeassistant.core import ServiceCall

from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__package__)

ATTR_CONFIG_ENTRY_ID = "config_entry_id"


class EvccService:
    """The services are registered once for the domain. With more than one evcc
    instance configured, a call picks its instance through 'config_entry_id'."""

    def __init__(self, hass):
        self._hass = hass

    def _coordinator(self, call: ServiceCall):
        # hass.data[DOMAIN] maps 'entry_id -> coordinator' (+ a 'manifest_version' string entry)
        coordinators = {key: value for key, value in self._hass.data.get(DOMAIN, {}).items() if key != "manifest_version"}
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID, None)
        if entry_id is not None:
            coordinator = coordinators.get(entry_id, None)
            if coordinator is None:
                _LOGGER.warning(f"{call.service}: unknown or not loaded config_entry_id '{entry_id}'")
            return coordinator

        if len(coordinators) > 1:
            # keep the previous behavior (the instance set up last) for existing automations
            _LOGGER.warning(f"{call.service}: {len(coordinators)} evcc instances are configured, but no 'config_entry_id' was provided - using the instance that was set up last")
        return list(coordinators.values())[-1] if len(coordinators) > 0 else None

    @staticmethod
    def _no_instance(call: ServiceCall):
        if call.return_response:
            return {
                "error": f"No evcc instance found for config_entry_id '{call.data.get(ATTR_CONFIG_ENTRY_ID, None)}'",
                "date": str(datetime.datetime.now().time())
            }
        return None

    async def set_loadpoint_plan(self, call: ServiceCall):
        return await self.set_plan(call)

    async def set_vehicle_plan(self, call: ServiceCall):
        """Set vehicle plan directly by vehicle name/id."""
        return await self.set_plan(call)

    async def set_plan(self, call: ServiceCall):
        coordinator = self._coordinator(call)
        if coordinator is None:
            return self._no_instance(call)

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
            available_vehicles = list(coordinator._vehicle.keys())
            _LOGGER.debug(f"Available vehicles: {available_vehicles}")
        else:
            available_vehicles = []

        # Validate input
        if input_date_str is not None:
            try:
                # date is YYYY-MM-DD HH:MM.SSS -> need to convert it to a UTC based RFC3339
                # 1. Parse naive string
                start = datetime.datetime.strptime(input_date_str, "%Y-%m-%d %H:%M:%S")
                start = start.replace(second=0)

                # 2. Get HA's configured local timezone (e.g., "Europe/Paris" or "America/New_York")
                # 3. Mark as HA local time, then convert to UTC
                start_local = start.replace(tzinfo=zoneinfo.ZoneInfo(self._hass.config.time_zone))
                start_utc = start_local.astimezone(datetime.timezone.utc)
                rfc_date = start_utc.isoformat(timespec="milliseconds").replace("+00:00", "Z")

                # Vehicle plan
                if vehicle_name is not None and vehicle_name in available_vehicles and isinstance(soc, int) and soc > 0:
                    resp = await coordinator.async_write_plan(vehicle_name, None, str(int(soc)), rfc_date, precondition)

                # Loadpoint plan
                elif loadpoint is not None and isinstance(loadpoint, int) and isinstance(energy, int) and energy > 0:
                    resp = await coordinator.async_write_plan(None, str(int(loadpoint)), str(int(energy)), rfc_date, None)

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
        coordinator = self._coordinator(call)
        if coordinator is None:
            return self._no_instance(call)

        # vehicle plan data
        vehicle_name = call.data.get("vehicle", None)

        # loadpoint plan data
        loadpoint = call.data.get("loadpoint", None)

        if vehicle_name:
            # Get available vehicles...
            available_vehicles = list(coordinator._vehicle.keys())
            _LOGGER.debug(f"Available vehicles: {available_vehicles}")
        else:
            available_vehicles = []

        # Validate input
        if vehicle_name is not None or loadpoint is not None:
            try:

                # Vehicle plan
                if vehicle_name is not None and vehicle_name in available_vehicles:
                    resp = await coordinator.async_delete_plan(vehicle_name, None)

                # Loadpoint plan
                elif loadpoint is not None and isinstance(loadpoint, int):
                    resp = await coordinator.async_delete_plan(None, str(int(loadpoint)))

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


    async def activate_loadpoint(self, call: ServiceCall):
        return await self.deactivate_loadpoint_internal(False, call)

    async def deactivate_loadpoint(self, call: ServiceCall):
        return await self.deactivate_loadpoint_internal(True, call)

    async def deactivate_loadpoint_internal(self, new_state: bool, call: ServiceCall):
        coordinator = self._coordinator(call)
        if coordinator is None:
            return self._no_instance(call)

        # loadpoint plan data
        loadpoint = call.data.get("loadpoint", None)

        # Validate input
        if loadpoint is not None:
            try:
                # Loadpoint plan
                if loadpoint is not None and isinstance(loadpoint, int):
                    resp = await coordinator.async_deactivate_loadpoint(new_state, int(loadpoint) -1 )
                else:
                    resp = None

                if resp is not None and len(resp) > 0:
                    if call.return_response:
                        if isinstance(resp, dict):
                            a_return_msg = resp.get("evcc_intg_message")
                            a_return_err = resp.get("evcc_intg_error")
                            if a_return_err and a_return_msg:
                                return {
                                    "success": "false",
                                    "date": str(datetime.datetime.now().time()),
                                    "response": {"error": a_return_err,
                                                 "message": a_return_msg}
                                }
                            elif a_return_msg:
                                return {
                                    "success": "true",
                                    "date": str(datetime.datetime.now().time()),
                                    "response": {"message": a_return_msg}
                                }

                        # our default "OK" response...
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
