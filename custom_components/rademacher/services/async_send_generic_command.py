"""Service implementations for Rademacher integration."""
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homepilot.api import AuthError

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Service constants
SERVICE_SEND_GENERIC_COMMAND = "send_generic_device_command"
ATTR_ENTITY_ID = "entity_id"
ATTR_COMMAND = "command"
ATTR_VALUE = "value"

# Service schemas
SERVICE_SEND_GENERIC_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_COMMAND): cv.string,
        vol.Required(ATTR_VALUE): vol.Any(cv.string),
    }
)


async def async_send_generic_command(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    """Handle the send_generic_device_command service call."""
    entity_id = call.data[ATTR_ENTITY_ID]
    command = call.data[ATTR_COMMAND]
    value = call.data[ATTR_VALUE]

    # Validate entity exists in registry
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)

    if entity_entry is None:
        raise ServiceValidationError(
            f"Entity {entity_id} not found in entity registry"
        )

    if entity_entry.platform != DOMAIN:
        raise ServiceValidationError(
            f"Entity {entity_id} does not belong to the {DOMAIN} integration"
        )

    # Get entity from component
    comp = hass.data["entity_components"][entity_id.split(".")[0]]
    entity = comp.get_entity(entity_id)        
    if entity is None:
        raise ServiceValidationError(
            f"Entity {entity_id} not found in entity component"
        )
    if not hasattr(entity, "did"):
        raise ServiceValidationError(
            f"Entity {entity_id} is not a Rademacher HomePilot entity"
        )
    did = entity.did    

    # Get manager and API
    config_entry_id = entity_entry.config_entry_id
    if config_entry_id not in hass.data[DOMAIN]:
        raise ServiceValidationError(
            f"Config entry for entity {entity_id} is not loaded"
        )

    manager = hass.data[DOMAIN][config_entry_id][0]
    api = manager.api  

    try:            
        _LOGGER.info(
            "Sending command '%s' with value '%s' to device %s (entity: %s)",
            command,
            value,
            did,
            entity_id
        )            
        
        response = await api.async_send_device_command(
            did=did,
            command=command,
            value=value
        )
        
        _LOGGER.debug("API response: %s", response)            
        return {"response": response}
        
    except AuthError as err:
        raise ServiceValidationError(
            f"Authentication failed for entity {entity_id}: {err}"
        ) from err
    except Exception as err:
        raise ServiceValidationError(
            f"Failed to send command '{command}' to entity {entity_id}: {err}"
        ) from err


async def async_register_generic_command_service(hass: HomeAssistant) -> None:
    """Register the generic device command service."""
    
    # Register generic device command service
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_GENERIC_COMMAND,
        lambda call: async_send_generic_command(hass, call),
        schema=SERVICE_SEND_GENERIC_COMMAND_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    _LOGGER.debug("Registered generic device command service")


async def async_unregister_generic_command_service(hass: HomeAssistant) -> None:
    """Unregister the generic device command service."""
    
    # Remove generic device command service
    hass.services.async_remove(DOMAIN, SERVICE_SEND_GENERIC_COMMAND)
    
    _LOGGER.debug("Unregistered generic device command service")