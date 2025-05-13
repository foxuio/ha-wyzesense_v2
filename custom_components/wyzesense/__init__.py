"""WyzeSense integration for Home Assistant."""
from homeassistant.core import HomeAssistant

DOMAIN = "wyzesense"

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the WyzeSense integration."""
    return True