import logging
from dataclasses import replace

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EvccDataUpdateCoordinator, EvccBaseEntity, ADDITIONAL_ENDPOINTS_DATA_EVCCCONF, EP_TYPE
from .const import DOMAIN, BUTTONS_ENTITIES, BUTTONS_ENTITIES_PER_LOADPOINT, ExtButtonEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("BUTTON async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    configuration_data_available = False
    if len(coordinator.data.get(ADDITIONAL_ENDPOINTS_DATA_EVCCCONF, {})) > 0:
        configuration_data_available = True

    entities = []
    for description in BUTTONS_ENTITIES:
        # enable all CONFIGURATION entities if config-data is available
        if configuration_data_available and description.tag.type == EP_TYPE.EVCCCONF:
            if not description.entity_registry_enabled_default:
                description = replace(
                    description,
                    entity_registry_enabled_default = True
                )

        entity = EvccButton(coordinator, description)
        entities.append(entity)

    multi_loadpoint_config = len(coordinator._loadpoint) > 1
    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]
        lp_has_phase_auto_option = load_point_config["has_phase_auto_option"]
        lp_is_heating = load_point_config["is_heating"]
        lp_is_integrated = load_point_config["is_integrated"]

        for a_stub in BUTTONS_ENTITIES_PER_LOADPOINT:
            if not lp_is_integrated or a_stub.integrated_supported:
                force_enable_by_default = configuration_data_available and a_stub.tag.type == EP_TYPE.EVCCCONF
                the_key = a_stub.tag.entity_key if a_stub.tag.entity_key is not None else a_stub.tag.json_key
                description = ExtButtonEntityDescription(
                    tag=a_stub.tag,
                    lp_idx=lp_api_index,
                    key=f"{lp_id_addon}_{the_key}",
                    translation_key=the_key,
                    name_addon=lp_name_addon if multi_loadpoint_config else None,
                    icon=a_stub.icon,
                    device_class=a_stub.device_class,
                    unit_of_measurement=a_stub.unit_of_measurement,
                    entity_category=a_stub.entity_category,
                    entity_registry_enabled_default=True if force_enable_by_default else a_stub.entity_registry_enabled_default,
                    is_lp_integrated_device=lp_is_integrated,

                    # the entity type specific values...
                    payload=a_stub.payload
                )

                entity = EvccButton(coordinator, description)
                entities.append(entity)

    add_entity_cb(entities)


class EvccButton(EvccBaseEntity, ButtonEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtButtonEntityDescription):
        super().__init__(entity_type=Platform.BUTTON, coordinator=coordinator, description=description)

    async def async_press(self, **kwargs):
        try:
            await self.coordinator.async_press_tag(self.tag, self.entity_description.payload, self.lp_idx, self)
        except ValueError:
            return "unavailable"