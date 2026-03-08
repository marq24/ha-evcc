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

        if not USE_NEW_FRIENDLY_NAME:
            return result

        # Check if child class implements _friendly_name_internal
        if not hasattr(self, '_friendly_name_internal') or not callable(getattr(self, '_friendly_name_internal', None)):
            return result

        # Check if we have a cached friendly name that matches what we would generate
        custom_friendly_name = self._friendly_name_internal()

        # Only modify if we have a custom name and it differs from cache
        if custom_friendly_name is not None:
            state, attr, original_name, capability_attr, original_device_class, supported_features = result

            # Patch the ATTR_FRIENDLY_NAME in the attributes dict
            if attr is not None and attr.get(ATTR_FRIENDLY_NAME, None) != custom_friendly_name:
                #_LOGGER.debug(f"Patching friendly name for {self.entity_id}: '{attr.get(ATTR_FRIENDLY_NAME)}' -> '{custom_friendly_name}'")
                attr[ATTR_FRIENDLY_NAME] = custom_friendly_name
                return (state, attr, original_name, capability_attr, original_device_class, supported_features)

        return result