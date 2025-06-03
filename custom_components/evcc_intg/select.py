import asyncio
import logging

from custom_components.evcc_intg.pyevcc_ha.const import MIN_CURRENT_LIST, MAX_CURRENT_LIST
from custom_components.evcc_intg.pyevcc_ha.keys import Tag
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import EvccDataUpdateCoordinator, EvccBaseEntity
from .const import DOMAIN, SELECT_SENSORS, SELECT_SENSORS_PER_LOADPOINT, ExtSelectEntityDescription

_LOGGER = logging.getLogger(__name__)
entities_min_max_dict = {}
SOCS_TAG_LIST = [Tag.PRIORITYSOC, Tag.BUFFERSOC, Tag.BUFFERSTARTSOC]

async def check_min_max():
    _LOGGER.debug("SELECT scheduled min_max check")
    try:
        await asyncio.sleep(15)
        if entities_min_max_dict is not None:
            size = len(entities_min_max_dict)
            count = 1
            for a_entity in entities_min_max_dict.values():
                a_entity.check_tag(size == count)
                count += 1

            _LOGGER.debug("SELECT init is COMPLETED")
    except BaseException as err:
        _LOGGER.warning(f"SELECT Error in check_min_max: {type(err)} {err}")


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, add_entity_cb: AddEntitiesCallback):
    _LOGGER.debug("SELECT async_setup_entry")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    global entities_min_max_dict
    entities_min_max_dict = {}

    entities = []
    for description in SELECT_SENSORS:
        entity = EvccSelect(coordinator, description)
        entities.append(entity)
        if description.tag in SOCS_TAG_LIST:
            entities_min_max_dict[entity.entity_id.split('.')[1].lower()] = entity

    multi_loadpoint_config = len(coordinator._loadpoint) > 1
    for a_lp_key in coordinator._loadpoint:
        load_point_config = coordinator._loadpoint[a_lp_key]
        lp_api_index = int(a_lp_key)
        lp_id_addon = load_point_config["id"]
        lp_name_addon = load_point_config["name"]
        lp_has_phase_auto_option = load_point_config["has_phase_auto_option"]
        lp_is_heating = load_point_config["is_heating"]

        for a_stub in SELECT_SENSORS_PER_LOADPOINT:
            description = ExtSelectEntityDescription(
                tag=a_stub.tag,
                idx=lp_api_index,
                key=f"{lp_id_addon}_{a_stub.tag.key}",
                translation_key=a_stub.tag.key,
                name_addon=lp_name_addon if multi_loadpoint_config else None,
                icon=a_stub.icon,
                device_class=a_stub.device_class,
                unit_of_measurement=a_stub.unit_of_measurement,
                entity_category=a_stub.entity_category,
                entity_registry_enabled_default=a_stub.entity_registry_enabled_default,

                # the entity type specific values...
                options=["null"] + list(
                    coordinator._vehicle.keys()) if a_stub.tag == Tag.VEHICLENAME else a_stub.tag.options,
            )

            # we might need to patch(remove) the 'auto-mode' from the phases selector
            if a_stub.tag == Tag.PHASES and not lp_has_phase_auto_option:
                description.options = description.options[1:]
                description.translation_key = f"{description.translation_key}_fixed"

            entity = EvccSelect(coordinator, description)

            if entity.tag == Tag.MINCURRENT or entity.tag == Tag.MAXCURRENT:
                entities_min_max_dict[entity.entity_id.split('.')[1].lower()] = entity

            entities.append(entity)

    add_entity_cb(entities)
    asyncio.create_task(check_min_max())


class EvccSelect(EvccBaseEntity, SelectEntity):
    def __init__(self, coordinator: EvccDataUpdateCoordinator, description: ExtSelectEntityDescription):
        super().__init__(coordinator=coordinator, description=description)

    async def add_to_platform_finish(self) -> None:
        if self.tag == Tag.VEHICLENAME:
            # ok we're going to patch the display strings for the vehicle names... this is quite a HACK!
            for a_key in self.coordinator._vehicle.keys():
                self.platform.platform_translations[
                    f"component.{DOMAIN}.entity.select.{Tag.VEHICLENAME.key.lower()}.state.{a_key.lower()}"] = self.coordinator._vehicle[a_key]["name"]
            #_LOGGER.error(f"-> {self.platform.platform_translations}")
        elif self.tag == Tag.VEHICLEMINSOC:
            #_LOGGER.error(f"{self.platform.platform_translations}")
            pass

        await super().add_to_platform_finish()

    def check_tag(self, is_last: bool = False):
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
                    _LOGGER.info("SELECT Skipping async_schedule_update_ha_state, since hass object is None?!")
        except BaseException as err:
            _LOGGER.debug(f"SELECT Error in check_tag for '{self.tag}' {self.entity_id} {type(err)} {err}")

    def _check_min_options(self, new_max_option: str):
        try:
            min_key = self.entity_id.split('.')[1].replace(Tag.MAXCURRENT.snake_case, Tag.MINCURRENT.snake_case)
            #_LOGGER.warning(f"CHECK_MIN {min_key} {entities_min_max_dict} {MIN_CURRENT_LIST} {entities_min_max_dict[min_key]}")
            if min_key in entities_min_max_dict:
                if new_max_option in MIN_CURRENT_LIST:
                    entities_min_max_dict[min_key].options = MIN_CURRENT_LIST[:MIN_CURRENT_LIST.index(new_max_option) + 1]
                else:
                    entities_min_max_dict[min_key].options = MIN_CURRENT_LIST

        except BaseException as err:
            _LOGGER.debug(f"SELECT Error _check_min_options for '{new_max_option}' {self.entity_id} {self.tag} {err}")

    def _check_max_options(self, new_min_option: str):
        try:
            max_key = self.entity_id.split('.')[1].replace(Tag.MINCURRENT.snake_case, Tag.MAXCURRENT.snake_case)
            #_LOGGER.warning(f"CHECK_MAX {max_key} {entities_min_max_dict} {MAX_CURRENT_LIST} {entities_min_max_dict[max_key]}")
            if max_key in entities_min_max_dict:
                if new_min_option in MAX_CURRENT_LIST:
                    entities_min_max_dict[max_key].options = MAX_CURRENT_LIST[MAX_CURRENT_LIST.index(new_min_option):]
                else:
                    entities_min_max_dict[max_key].options = MAX_CURRENT_LIST

        except BaseException as err:
            _LOGGER.debug(f"SELECT Error _check_max_options for '{new_min_option}' {self.entity_id} {self.tag} {err}")

    def _check_socs(self, option: str):
        try:
            changed_option = self.entity_id.split('.')[1].split('_')
            system_id = changed_option[0]
            changed_option_key = '_'.join(changed_option[1:])

            #_LOGGER.warning(f"SOC CHECK: {system_id} {changed_option_key} {entities_min_max_dict}")

            # is 'Vehicle first' (BUFFERSOC)
            if changed_option_key == Tag.BUFFERSOC.snake_case:
                # we need to adjust the 'Support vehicle charging' (BUFFERSTARTSOC) options
                select = entities_min_max_dict[f"{system_id}_{Tag.BUFFERSTARTSOC.snake_case}"]
                if option in Tag.BUFFERSTARTSOC.options:
                    select.options = Tag.BUFFERSTARTSOC.options[Tag.BUFFERSTARTSOC.options.index(option):]
                else:
                    select.options = Tag.BUFFERSTARTSOC.options

                # we need to adjust the 'Home has priority' (PRIORITYSOC) options
                select = entities_min_max_dict[f"{system_id}_{Tag.PRIORITYSOC.snake_case}"]
                if int(option) > 0 and option in Tag.PRIORITYSOC.options:
                    select.options = Tag.PRIORITYSOC.options[:Tag.PRIORITYSOC.options.index(option)+1]
                else:
                    select.options = Tag.PRIORITYSOC.options

            # is 'Home has priority' (PRIORITYSOC)
            elif changed_option_key == Tag.PRIORITYSOC.snake_case:
                # we need to adjust the 'Vehicle first' (BUFFERSOC) options
                select = entities_min_max_dict[f"{system_id}_{Tag.BUFFERSOC.snake_case}"]
                if option in Tag.BUFFERSOC.options:
                    select.options = Tag.BUFFERSOC.options[Tag.BUFFERSOC.options.index(option):]
                else:
                    select.options = Tag.BUFFERSOC.options

            # is 'Support vehicle charging' (BUFFERSTARTSOC)
            elif changed_option_key == Tag.BUFFERSTARTSOC.snake_case:
                # we need to adjust the 'Vehicle first' (BUFFERSOC) options
                low_option = entities_min_max_dict[f"{system_id}_{Tag.PRIORITYSOC.snake_case}"].current_option
                select = entities_min_max_dict[f"{system_id}_{Tag.BUFFERSOC.snake_case}"]
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
    def current_option(self) -> str | None:
        try:
            value = self.coordinator.read_tag(self.tag, self.idx)

            # _LOGGER.error(f"{self.tag.key} {self.idx} {value}")

            if value is None or value == "":
                # we must patch an empty vehicle_id to 'null' to avoid the select option being set to 'unknown'
                if self.tag.key == Tag.VEHICLENAME.key:
                    value = "null"
                else:
                    value = 'unknown'
            if isinstance(value, (int, float)):
                value = str(value)

        except KeyError as kerr:
            _LOGGER.debug(f"SELECT KeyError: '{self.tag}' '{self.idx}' {kerr}")
            value = "unknown"
        except TypeError as terr:
            _LOGGER.debug(f"SELECT TypeError: '{self.tag}' '{self.idx}' {terr}")
            value = None
        return value

    async def async_select_option(self, option: str) -> None:
        try:
            if str(option) == "null":
                await self.coordinator.async_write_tag(self.tag, None, self.idx, self)
            else:
                await self.coordinator.async_write_tag(self.tag, option, self.idx, self)

            if self.tag == Tag.MAXCURRENT:
                self._check_min_options(option)
            elif self.tag == Tag.MINCURRENT:
                self._check_max_options(option)
            elif self.tag in SOCS_TAG_LIST:
                self._check_socs(option)

        except ValueError:
            return "unavailable"
