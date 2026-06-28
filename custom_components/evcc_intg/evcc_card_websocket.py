import logging
from typing import Final

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import EvccDataUpdateCoordinator
from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__package__)

# on-demand request/response commands that allow frontend cards (e.g. hass-evcc-card) to fetch evcc
# data that does not map well to entities: tariff/forecast time-series, the detailed charging
# session history and a read-only charging-plan preview. The card calls these via 'hass.callWS(...)'
# over the already authorized HA websocket connection - so ha-evcc performs the actual evcc call
# server-side (no CORS/mixed-content issues, no additional entities and no recorder load). The
# commands are registered once (globally) and resolve the target config-entry at call time via the
# provided 'entry_id'.

# advertised via the 'evcc_intg/capabilities' command - so a card can check what is supported
SUPPORTED_COMMANDS: Final = ["forecast", "sessions", "plan_preview"]
TARIFF_KINDS: Final = ["grid", "feedin", "solar", "planner"]
PLAN_PREVIEW_KINDS: Final = ["soc", "energy"]


def coordinator_for(hass: HomeAssistant, connection, msg) -> EvccDataUpdateCoordinator | None:
    # hass.data[DOMAIN] maps 'entry_id -> coordinator' (+ a 'manifest_version' string entry) - so an
    # explicit type check ignores that string value (and also handles any unknown entry_id)
    coordinator = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if not isinstance(coordinator, EvccDataUpdateCoordinator):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, f"unknown entry_id '{msg['entry_id']}'")
        return None
    return coordinator


@websocket_api.websocket_command({
    vol.Required("type"): "evcc_intg/forecast",
    vol.Required("entry_id"): str,
    vol.Required("kind"): vol.In(TARIFF_KINDS),
})
@websocket_api.async_response
async def extension_forecast_data(hass: HomeAssistant, connection, msg):
    coordinator = coordinator_for(hass, connection, msg)
    if coordinator is not None:
        rates = await coordinator.bridge.evcc_card_read_tariff(msg["kind"])
        # the rates carry no unit field - tell the card whether the 'value' fields are a price
        # (currency/kWh) or CO2 (g/kWh, when smartCostType is 'co2'), same enrichment as ws_plan_preview
        connection.send_result(msg["id"], {
            "kind": msg["kind"],
            **rates,
            "smartCostType": coordinator._cost_type,
            "currency": coordinator._currency,
        })


@websocket_api.websocket_command({
    vol.Required("type"): "evcc_intg/sessions",
    vol.Required("entry_id"): str,
    vol.Optional("year"): int,
    vol.Optional("month"): int,
})
@websocket_api.async_response
async def extension_session_data(hass: HomeAssistant, connection, msg):
    coordinator = coordinator_for(hass, connection, msg)
    if coordinator is not None:
        sessions = await coordinator.bridge.evcc_card_read_sessions_raw(msg.get("year", None), msg.get("month", None))
        connection.send_result(msg["id"], {"sessions": sessions})


@websocket_api.websocket_command({
    vol.Required("type"): "evcc_intg/plan_preview",
    vol.Required("entry_id"): str,
    vol.Required("loadpoint"): int,
    vol.Required("kind"): vol.In(PLAN_PREVIEW_KINDS),
    vol.Required("value"): vol.Coerce(str),
    vol.Required("timestamp"): str,
})
@websocket_api.async_response
async def extension_plan_preview(hass: HomeAssistant, connection, msg):
    coordinator = coordinator_for(hass, connection, msg)
    if coordinator is None:
        return

    lp_idx = str(msg["loadpoint"])
    result = await coordinator.bridge.evcc_card_read_loadpoint_plan_static_preview(lp_idx, msg["kind"], msg["value"], msg["timestamp"])

    # enrich the raw evcc response with the cost type and currency so the card knows whether
    # the plan slot 'value' fields represent a price (EUR/kWh) or CO2 (g/kWh)
    result["smartCostType"] = coordinator._cost_type
    result["currency"] = coordinator._currency
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "evcc_intg/capabilities",
    vol.Optional("entry_id"): str,
})
@callback
def extension_capabilities(hass: HomeAssistant, connection, msg):
    version = hass.data.get(DOMAIN, {}).get("manifest_version", "UNKNOWN")
    result = {"version": version, "commands": SUPPORTED_COMMANDS}

    # a frontend card that wants to target a specific loadpoint (e.g. for the
    # 'plan_preview' command) needs the evcc loadpoint index (1-based) - but that
    # index is not exposed through any entity state or attribute. The integration
    # knows it (it is the key of coordinator._loadpoint), so we hand out the
    # id -> index mapping here. 'entry_id' is optional for this command, so the
    # loadpoint list is only added when a matching coordinator is available.
    coordinator = hass.data.get(DOMAIN, {}).get(msg.get("entry_id"))
    if isinstance(coordinator, EvccDataUpdateCoordinator):
        result["loadpoints"] = [
            {
                "index": int(a_lp_key),
                "id": a_lp_cfg.get("id"),
                "name": a_lp_cfg.get("name"),
                "heating": a_lp_cfg.get("is_heating", False),
            }
            for a_lp_key, a_lp_cfg in coordinator._loadpoint.items()
        ]

    connection.send_result(msg["id"], result)


@callback
def async_register_evcc_card_websocket_commands(hass: HomeAssistant):
    websocket_api.async_register_command(hass, extension_forecast_data)
    websocket_api.async_register_command(hass, extension_session_data)
    websocket_api.async_register_command(hass, extension_plan_preview)
    websocket_api.async_register_command(hass, extension_capabilities)
