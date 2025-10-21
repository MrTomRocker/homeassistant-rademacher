"""Services for Rademacher integration."""

from .async_send_generic_command import async_register_generic_command_service

async def async_register_services(hass):
    """Register ALL services for the Rademacher integration."""
    await async_register_generic_command_service(hass)
