import logging

from awesomeversion import AwesomeVersion
from homeassistant.const import ATTR_FRIENDLY_NAME, __version__ as HA_VERSION
from homeassistant.helpers.entity import Entity

USE_NEW_FRIENDLY_NAME = AwesomeVersion(HA_VERSION) >= AwesomeVersion("2026.2.0")

_LOGGER = logging.getLogger(__name__)
#_LOGGER.debug(f"HA Version: {HA_VERSION}, USE_NEW_FRIENDLY_NAME: {USE_NEW_FRIENDLY_NAME}")


class CustomFriendlyNameEntity(Entity):

    def __init__(self, *args, **kwargs):
        """Initialize and check if method exists."""
        super().__init__(*args, **kwargs)

    # This is a SYNCHRONOUS method that returns a tuple, not async!
    def _Entity__async_calculate_state(self):
        """Calculate state and override ATTR_FRIENDLY_NAME."""

        # First let the base implementation calculate state (returns a tuple)
        result = super()._Entity__async_calculate_state()

        if not USE_NEW_FRIENDLY_NAME or self._attr_has_entity_name == False:
            return result

        # Check if child class implements _friendly_name_internal
        if not hasattr(self, '_friendly_name_internal') or not callable(getattr(self, '_friendly_name_internal', None)):
            return result

        # Check if we have a cached friendly name that matches what we would generate
        custom_friendly_name = self._friendly_name_internal()

        # Only modify if we have a custom name and it differs from cache
        if custom_friendly_name is not None:
            result_list = list(result)
            attr = None
            attr_index = None

            for i, item in enumerate(result_list):
                if isinstance(item, dict) and ATTR_FRIENDLY_NAME in item:
                    attr = item
                    attr_index = i
                    break

            if attr is None:
                _LOGGER.warning(f"Could not find friendly name attribute in state result for {self.entity_id}")
                return result

            # Only modify if we found the attr dict and it differs
            if attr.get(ATTR_FRIENDLY_NAME) != custom_friendly_name:
                attr[ATTR_FRIENDLY_NAME] = custom_friendly_name
                result_list[attr_index] = attr
                return tuple(result_list)

        return result