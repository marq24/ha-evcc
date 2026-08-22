from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {
    CONF_USERNAME,
    CONF_HOST,
    CONF_PASSWORD,
    "authProviders",
    "certificate",
    "url",
    "user",
    "org",
    "token",
    "clientID",
    "caCert",
    "clientCert",
    "clientKey",
    "externalUrl",
    "internalUrl",
    "sponsor",
    "@@@session-data@@@raw"
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data.get(DOMAIN,{}).get(config_entry.entry_id, None)
    if coordinator:
        coord_obj = {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
            "data": async_redact_data(coordinator.data, TO_REDACT) if coordinator.data else None,
        }
    else:
        coord_obj = {}

    return {
        "config_entry": {
            "data": async_redact_data(dict(config_entry.data), TO_REDACT),
            "options": async_redact_data(dict(config_entry.options), TO_REDACT),
        },
        "coordinator": coord_obj
    }
