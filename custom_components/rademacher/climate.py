"""Platform for Rademacher Bridge."""
import asyncio
import logging

from homepilot.device import HomePilotDevice
from homepilot.manager import HomePilotManager
from homepilot.thermostat import HomePilotThermostat

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode, HVACAction, PRESET_NONE, PRESET_BOOST 
from homeassistant.const import CONF_EXCLUDE, UnitOfTemperature
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .entity import HomePilotEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup of entities for sensor platform."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    manager: HomePilotManager = entry[0]
    coordinator: DataUpdateCoordinator = entry[1]
    exclude_devices: list[str] = entry[3][CONF_EXCLUDE]
    new_entities = []
    for did in manager.devices:
        if did not in exclude_devices:
            device: HomePilotDevice = manager.devices[did]
            if isinstance(device, HomePilotThermostat):
                _LOGGER.info("Found Thermostat for Device ID: %s", device.did)
                new_entities.append(
                    HomePilotClimateEntity(
                        coordinator,
                        device,
                        UnitOfTemperature.CELSIUS,
                    )
                )
    # If we have any new devices, add them
    if new_entities:
        async_add_entities(new_entities)


class HomePilotClimateEntity(HomePilotEntity, ClimateEntity):
    """This class represents all Sensors supported."""

    def __init__(
        self,
        coordinator,
        device: HomePilotThermostat,
        temperature_unit,
    ) -> None:
        super().__init__(
            coordinator,
            device,
            unique_id=f"{device.uid}",
            name=f"{device.name}",
            device_class=None,
        )
        self._attr_temperature_unit = temperature_unit
        self._attr_max_temp = device.max_target_temperature
        self._attr_min_temp = device.min_target_temperature
        self._attr_target_temperature_step = device.step_target_temperature
        self._attr_hvac_modes = (
            [HVACMode.AUTO, HVACMode.HEAT_COOL]
            if device.has_auto_mode
            else [HVACMode.HEAT_COOL]        
        )
        self._attr_hvac_action = HVACAction.IDLE if device.has_relais_status else None
        self._attr_preset_modes = [PRESET_NONE, PRESET_BOOST] if device.has_boost_active else None

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        device: HomePilotThermostat = self.coordinator.data[self.did]
        if device.has_auto_mode:
            await device.async_set_auto_mode(hvac_mode == HVACMode.AUTO)
            async with asyncio.timeout(5):
                await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        device: HomePilotThermostat = self.coordinator.data[self.did]
        if device.can_set_target_temperature:
            await device.async_set_target_temperature(kwargs["temperature"])
            async with asyncio.timeout(5):
                await self.coordinator.async_request_refresh()

    @property
    def current_temperature(self) -> float:
        device: HomePilotThermostat = self.coordinator.data[self.did]
        return device.temperature_value if device.has_temperature else None

    @property
    def target_temperature(self) -> float:
        device: HomePilotThermostat = self.coordinator.data[self.did]
        return (
            device.target_temperature_value if device.has_target_temperature else None
        )

    @property
    def hvac_mode(self) -> str:
        device: HomePilotThermostat = self.coordinator.data[self.did]
        return (
            HVACMode.AUTO
            if device.has_auto_mode and device.auto_mode_value
            else HVACMode.HEAT_COOL
        )

    @property
    def hvac_action(self) -> str:
        device: HomePilotThermostat = self.coordinator.data[self.did]
        if not device.has_relais_status:
            return None
        if device.relais_status:
            if self.current_temperature < self.target_temperature:
                return HVACAction.HEATING
            else:
                return HVACAction.COOLING
        else:   
            return HVACAction.IDLE
    
    @property
    def preset_mode(self) -> str | None:
        device: HomePilotThermostat = self.coordinator.data[self.did]
        if not device.has_boost_active:
            return None
        return PRESET_BOOST if device.boost_active_value else PRESET_NONE
    
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        device: HomePilotThermostat = self.coordinator.data[self.did]
        if not device.has_boost_active:
            return
        if preset_mode == PRESET_BOOST:
            await device.async_set_boost_active_cfg(True)
        else:
            await device.async_set_boost_active_cfg(False)
        async with asyncio.timeout(5):
            await self.coordinator.async_request_refresh()

    @property
    def supported_features(self) -> int:
        device: HomePilotThermostat = self.coordinator.data[self.did]
        feature = ClimateEntityFeature.TARGET_TEMPERATURE if device.can_set_target_temperature else 0
        feature |= ClimateEntityFeature.PRESET_MODE if device.has_boost_active else 0
        return feature
