import asyncio
import logging
from dataclasses import replace

from custom_components.evcc_intg.pyevcc_ha.const import MIN_CURRENT_LIST, MAX_CURRENT_LIST
from custom_components.evcc_intg.pyevcc_ha.keys import Tag
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, SELECT_ENTITIES, SELECT_ENTITIES_PER_LOADPOINT, ExtSelectEntityDescription

_LOGGER = logging.getLogger(__name__)
SOCS_TAG_LIST = [Tag.PRIORITYSOC, Tag.BUFFERSOC, Tag.BUFFERSTARTSOC]

async def check_min_max_after_init(coordinator: EvccDataUpdateCoordinator = None):
    _LOGGER.debug("check_min_max_after_init(): SELECT scheduled min_max check")
    try:
        await asyncio.sleep(15)
        if coordinator.select_entities_dict is not None:
            size = len(coordinator.select_entities_dict)
            count = 1
            for a_entity in coordinator.select_entities_dict.values():
                a_entity.check_tag_after_init(size == count)
                count += 1

            _LOGGER.debug("check_min_max_after_init(): SELECT init is COMPLETED")
    except BaseException as err:
        _LOGGER.warning(f"check_min_max_after_init(): SELECT Error in check_min_max: {type(err)} {err}")


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("SELECT async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for description in SELECT_ENTITIES:
        entity = EvccSelect(coordinator, description)
        entities.append(entity)
        if description.tag in SOCS_TAG_LIST:
            coordinator.select_entities_dict[description.tag] = entity

    multi_loadpoint_config = len(coordinator._loadpoint) > 1
    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]
        lp_has_phase_auto_option = load_point_config["has_phase_auto_option"]
        lp_is_heating = load_point_config["is_heating"]
        lp_is_integrated = load_point_config["is_integrated"]
        lp_is_single_phase_only = load_point_config["only_single_phase"]

        for a_stub in SELECT_ENTITIES_PER_LOADPOINT:
            if (not lp_is_single_phase_only or a_stub.tag != Tag.PHASES) and (not lp_is_integrated or a_stub.integrated_supported):
                description = ExtSelectEntityDescription(
                    tag=a_stub.tag,
                    lp_idx=lp_api_index,
                    key=f"{lp_id_addon}_{a_stub.tag.json_key}",
                    translation_key=a_stub.tag.json_key,
                    name_addon=lp_name_addon if multi_loadpoint_config else None,
                    icon=a_stub.icon,
                    device_class=a_stub.device_class,
                    unit_of_measurement=a_stub.unit_of_measurement,
                    entity_category=a_stub.entity_category,
                    entity_registry_enabled_default=a_stub.entity_registry_enabled_default,

                    # the entity type specific values...
                    options=["null"] + list(coordinator._vehicle.keys()) if a_stub.tag == Tag.LP_VEHICLENAME else a_stub.tag.options,
                )

                # we might need to patch(remove) the 'auto-mode' from the phases selector
                if a_stub.tag == Tag.PHASES and not lp_has_phase_auto_option:
                    description = replace(
                        description,
                        options = description.options[1:],
                        translation_key = f"{description.translation_key}_fixed"
                    )

                entity = EvccSelect(coordinator, description)

                if entity.tag == Tag.MINCURRENT or entity.tag == Tag.MAXCURRENT:
                    coordinator.select_entities_dict[entity.tag] = entity

                entities.append(entity)

    add_entity_cb(entities)
    asyncio.create_task(check_min_max_after_init(coordinator))


class EvccSelect(EvccBaseEntity, SelectEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtSelectEntityDescription):
        super().__init__(entity_type=Platform.SELECT, coordinator=coordinator, description=description)

    async def add_to_platform_finish(self) -> None:
        if self.tag == Tag.LP_VEHICLENAME:

            has_pf_data = hasattr(self.platform, "platform_data")
            has_pf_trans = hasattr(self.platform.platform_data, "platform_translations") if has_pf_data else hasattr(self.platform, "platform_translations")
            has_pf_default_lang_trans = hasattr(self.platform.platform_data, "default_language_platform_translations") if has_pf_data else hasattr(self.platform, "default_language_platform_translations")

            # ok we're going to patch the display strings for the vehicle names... this is quite a HACK!
            for a_key in self.coordinator._vehicle.keys():
                a_trans_key = f"component.{DOMAIN}.entity.select.{Tag.LP_VEHICLENAME.json_key.lower()}.state.{a_key.lower()}"
                a_value = self.coordinator._vehicle[a_key]["name"]
                if has_pf_data:
                    if has_pf_trans:
                        self.platform.platform_data.platform_translations[a_trans_key] = a_value
                    if has_pf_default_lang_trans:
                        self.platform.platform_data.default_language_platform_translations[a_trans_key] = a_value
                else:
                    # old HA compatible version...
                    if has_pf_trans:
                        self.platform.platform_translations[a_trans_key] = a_value
                    if has_pf_default_lang_trans:
                        self.platform.default_language_platform_translations[a_trans_key] = a_value

                #_LOGGER.debug(f"added vehicle-translation-key: evcc: '{a_key}' name: '{a_value}' key: {a_trans_key}")
            #_LOGGER.info(f"-> {self.platform.platform_data.platform_translations}")
            #_LOGGER.info("----------------")
            #_LOGGER.info(f"-> {self.platform.platform_data.default_language_platform_translations}")

        elif self.tag == Tag.VEHICLEMINSOC:
            #_LOGGER.error(f"{self.platform.platform_data.platform_translations}")
            pass

        await super().add_to_platform_finish()

    def check_tag_after_init(self, is_last: bool = False):
        try:
            if self.tag == Tag.MAXCURRENT:
                self._check_min_options(self.current_option)
            elif self.tag == Tag.MINCURRENT:
                self._check_max_options(self.current_option)
            elif self.tag in SOCS_TAG_LIST:
                self._check_socs(self.current_option)

            if is_last:
                if self.hass is not None:
                    self.async_schedule_update_ha_state(force_refresh=True)
                else:
                    _LOGGER.info("check_tag_after_init(): SELECT Skipping async_schedule_update_ha_state, since hass object is None?!")
        except BaseException as err:
            _LOGGER.debug(f"check_tag_after_init(): SELECT Error in check_tag_after_init for '{self.tag}' {self.entity_id} {type(err)} {err}")

    def _check_min_options(self, new_max_option: str):
        try:
            min_key = Tag.MINCURRENT
            #_LOGGER.warning(f"CHECK_MIN {min_key} {MIN_CURRENT_LIST} {self.coordinator.entities_min_max_dict[min_key]}")
            if min_key in self.coordinator.select_entities_dict:
                if new_max_option in MIN_CURRENT_LIST:
                    self.coordinator.select_entities_dict[min_key].options = MIN_CURRENT_LIST[:MIN_CURRENT_LIST.index(new_max_option) + 1]
                else:
                    self.coordinator.select_entities_dict[min_key].options = MIN_CURRENT_LIST

        except BaseException as err:
            _LOGGER.debug(f"SELECT Error _check_min_options for '{new_max_option}' {self.entity_id} {self.tag} {err}")

    def _check_max_options(self, new_min_option: str):
        try:
            max_key = Tag.MAXCURRENT
            #_LOGGER.warning(f"CHECK_MAX {max_key} {MAX_CURRENT_LIST} {self.coordinator.entities_min_max_dict[max_key]}")
            if max_key in self.coordinator.select_entities_dict:
                if new_min_option in MAX_CURRENT_LIST:
                    self.coordinator.select_entities_dict[max_key].options = MAX_CURRENT_LIST[MAX_CURRENT_LIST.index(new_min_option):]
                else:
                    self.coordinator.select_entities_dict[max_key].options = MAX_CURRENT_LIST

        except BaseException as err:
            _LOGGER.debug(f"SELECT Error _check_max_options for '{new_min_option}' {self.entity_id} {self.tag} {err}")

    def _check_socs(self, option: str):
        try:
            #_LOGGER.warning(f"SOC CHECK caused by: {self.tag}")

            # is 'Vehicle first' (BUFFERSOC)
            if self.tag == Tag.BUFFERSOC:
                # we need to adjust the 'Support vehicle charging' (BUFFERSTARTSOC) options
                select = self.coordinator.select_entities_dict[Tag.BUFFERSTARTSOC]
                if option in Tag.BUFFERSTARTSOC.options:
                    select.options = Tag.BUFFERSTARTSOC.options[Tag.BUFFERSTARTSOC.options.index(option):]
                else:
                    select.options = Tag.BUFFERSTARTSOC.options

                # we need to adjust the 'Home has priority' (PRIORITYSOC) options
                select = self.coordinator.select_entities_dict[Tag.PRIORITYSOC]
                if int(option) > 0 and option in Tag.PRIORITYSOC.options:
                    select.options = Tag.PRIORITYSOC.options[:Tag.PRIORITYSOC.options.index(option)+1]
                else:
                    select.options = Tag.PRIORITYSOC.options

            # is 'Home has priority' (PRIORITYSOC)
            elif self.tag == Tag.PRIORITYSOC:
                # we need to adjust the 'Vehicle first' (BUFFERSOC) options
                select = self.coordinator.select_entities_dict[Tag.BUFFERSOC]
                if option in Tag.BUFFERSOC.options:
                    select.options = Tag.BUFFERSOC.options[Tag.BUFFERSOC.options.index(option):]
                else:
                    select.options = Tag.BUFFERSOC.options

            # is 'Support vehicle charging' (BUFFERSTARTSOC)
            elif self.tag == Tag.BUFFERSTARTSOC:
                # we need to adjust the 'Vehicle first' (BUFFERSOC) options
                low_option = self.coordinator.select_entities_dict[Tag.PRIORITYSOC].current_option
                select = self.coordinator.select_entities_dict[Tag.BUFFERSOC]
                if int(option) > 0 and option in Tag.BUFFERSOC.options and low_option in Tag.BUFFERSOC.options:
                    select.options = Tag.BUFFERSOC.options[Tag.BUFFERSOC.options.index(low_option):Tag.BUFFERSOC.options.index(option)+1]
                elif int(option) > 0 and option in Tag.BUFFERSOC.options:
                    select.options = Tag.BUFFERSOC.options[:Tag.BUFFERSOC.options.index(option)+1]
                else:
                    if low_option in Tag.BUFFERSOC.options:
                        select.options = Tag.BUFFERSOC.options[Tag.BUFFERSOC.options.index(low_option):]
                    else:
                        select.options = Tag.BUFFERSOC.options

        except BaseException as err:
            _LOGGER.debug(f"SELECT Error _check_socs for '{option}' {self.entity_id} {self.tag} {err}")

    # def _on_vehicle_change(self, sel_vehicle_id: str):
    #     if JSONKEY_VEHICLES in self.coordinator.data and sel_vehicle_id in self.coordinator.data[JSONKEY_VEHICLES]:
    #         veh_dict = self.coordinator.data[JSONKEY_VEHICLES][sel_vehicle_id]
    #         if Tag.VEHICLEMINSOC.key in veh_dict:
    #             val_minsoc = veh_dict[Tag.VEHICLEMINSOC.key]
    #         else:
    #             val_minsoc = "0"
    #         if Tag.VEHICLELIMITSOC.key in veh_dict:
    #             val_limitsoc = veh_dict[Tag.VEHICLELIMITSOC.key]
    #         else:
    #             val_limitsoc = "0"

    @property
    def extra_state_attributes(self):
        """Return select attributes"""
        if Tag.LP_VEHICLENAME == self.tag:
            a_key = self.current_option
            if isinstance(a_key, str) and a_key in self.coordinator._vehicle:
                return {"vehicle": self.coordinator._vehicle[a_key]}
        return None

    @property
    def current_option(self) -> str | None:
        try:
            value = self.coordinator.read_tag(self.tag, self.lp_idx)
            # _LOGGER.error(f"{self.tag.json_key} {self.lp_idx} {value}")
            if value is None or value == "":
                # we must patch an empty vehicle_id to 'null' to avoid the select option being set to 'unknown'
                if Tag.LP_VEHICLENAME.json_key == self.tag.json_key:
                    value = "null"
                else:
                    value = 'unknown'
            if isinstance(value, (int, float)):
                value = str(value)

            #if self.tag == Tag.LP_VEHICLENAME and isinstance(value, str):
            #    # when we read from the API a value like 'db:12' we MUST convert it
            #    # to our local format 'db_12' ... since HA can't handle the ':'
            #    value = value.replace(':', '_')

        except KeyError as kerr:
            _LOGGER.debug(f"SELECT KeyError: '{self.tag}' '{self.lp_idx}' {kerr}")
            value = "unknown"
        except TypeError as terr:
            _LOGGER.debug(f"SELECT TypeError: '{self.tag}' '{self.lp_idx}' {terr}")
            value = None
        return value

    async def async_select_option(self, option: str) -> None:
        try:
            if "null" == str(option):
                await self.coordinator.async_write_tag(self.tag, None, self.lp_idx, self)
            else:
                #if Tag.LP_VEHICLENAME == self.tag:
                #    # me must map the value selected in the select.options to the final value
                #    # that is used in EVCC as identifier (can be a value like 'db:12') - but
                #    # HA can't deal correctly with the ':'
                #    if option in self.coordinator._vehicle:
                #        option = self.coordinator._vehicle[option][EVCC_JSON_VEH_NAME]

                await self.coordinator.async_write_tag(self.tag, option, self.lp_idx, self)

            #_LOGGER.info(f"{self.tag} CHANGED to '{option}'")
            if self.tag == Tag.MAXCURRENT:
                self._check_min_options(option)

            elif self.tag == Tag.MINCURRENT:
                self._check_max_options(option)

            elif self.tag in SOCS_TAG_LIST:
                self._check_socs(option)

        except ValueError:
            return "unavailable"
