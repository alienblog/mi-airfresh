"""Support for Xiaomi Mi Air Fresh t2017"""
import asyncio
from enum import Enum
from functools import partial
import logging
from typing import Any, Dict, Optional
from collections import defaultdict

import voluptuous as vol

from homeassistant.components.fan import (FanEntity, PLATFORM_SCHEMA,
                                          SUPPORT_SET_SPEED, DOMAIN, )
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_TOKEN,
                                 ATTR_ENTITY_ID, )
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Xiaomi Miio Device t2017'
DATA_KEY = 'fan.dairfresh'

CONF_MODEL = 'model'

ATTR_PM25 = 'pm25'
ATTR_MODE = 'mode'
ATTR_CO2 = 'co2'
ATTR_OUTTEMP = 'temperature_outside'
ATTR_FAVSPD = 'favourite_speed'
ATTR_CTLSPD = 'control_speed'
ATTR_FTRINTERMEDIATE = 'filter_intermediate'
ATTR_FTRINTERDAY = 'filter_inter_day'
ATTR_FTREFFICIENT = 'filter_efficient'
ATTR_FTREFFIDAY = 'filter_effi_day'
ATTR_PTCON = 'ptc_on'
ATTR_PTCLEVEL = 'ptc_level'
ATTR_PTCSTATUS = 'ptc_status'
ATTR_CHILDLOCK = 'child_lock'
ATTR_SOUND = 'sound'
ATTR_DISPLAY = 'display'
ATTR_SCNDIR = 'screen_direction'

SUCCESS = ['ok']

AVAILABLE_ATTRIBUTES_AIRFRESH = {
    ATTR_PM25: 'pm25',
    ATTR_CO2: 'co2',
    ATTR_MODE: 'mode',
    ATTR_OUTTEMP: 'temperature_outside',
    ATTR_FAVSPD: 'favourite_speed',
    ATTR_CTLSPD: 'control_speed',
    ATTR_FTRINTERMEDIATE: 'filter_intermediate',
    ATTR_FTRINTERDAY: 'filter_inter_day',
    ATTR_FTREFFICIENT: 'filter_efficient',
    ATTR_FTREFFIDAY: 'filter_effi_day',
    ATTR_PTCON: 'ptc_on',
    ATTR_PTCLEVEL: 'ptc_level',
    ATTR_PTCSTATUS: 'ptc_status',
    ATTR_CHILDLOCK: 'child_lock',
    ATTR_SOUND: 'sound',
    ATTR_DISPLAY: 'display',
    ATTR_SCNDIR: 'screen_direction'
}

FEATURE_SET_BUZZER = 1
FEATURE_SET_LED = 2
FEATURE_SET_CHILD_LOCK = 4
FEATURE_SET_LED_BRIGHTNESS = 8
FEATURE_SET_FAVORITE_LEVEL = 16
FEATURE_SET_AUTO_DETECT = 32
FEATURE_SET_LEARN_MODE = 64
FEATURE_SET_VOLUME = 128
FEATURE_RESET_FILTER = 256
FEATURE_SET_EXTRA_FEATURES = 512
FEATURE_SET_TARGET_HUMIDITY = 1024
FEATURE_SET_DRY = 2048

FEATURE_FLAGS_DAIRFRESH = (FEATURE_SET_CHILD_LOCK |
                                 FEATURE_SET_LED |
                                 FEATURE_SET_FAVORITE_LEVEL |
                                 FEATURE_SET_AUTO_DETECT |
                                 FEATURE_SET_VOLUME)
MODEL_DAIRFRESH_T2017 = 'dmaker.airfresh.t2017'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MODEL): vol.In(
        [MODEL_DAIRFRESH_T2017]),
})

OPERATION_MODES_AIRFRESH = ['Off', 'Auto', 'Sleep', 'Favourite']
OPERATION_LEVELS_PTC = ['Off', 'Low', 'Medium', 'High']

ATTR_MODEL = 'model'

class OperationMode(Enum):
    # Supported modes of the Air Fresh T2017 (dmaker.airfresh.t2017)
    Off = 'off'
    Auto = 'auto'
    Sleep = 'sleep'
    Favourite = 'favourite'

class OperationPTCLevel(Enum):
    Off = 'off'
    Low = 'low'
    Medium = 'medium'
    High = 'high'

class DisplayOrientation(Enum):
    Portrait = "forward"
    LandscapeLeft = "left"
    LandscapeRight = "right"

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the miio fan device from config."""
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    token = config.get(CONF_TOKEN)
    model = config.get(CONF_MODEL)

    _LOGGER.info("Initializing with host %s (token %s...)", host, token[:5])
    unique_id = None

    if model is None:
        model = 'dmaker.airfresh.t2017'


    if model.startswith('dmaker.airfresh.t2017'):
        from miio import AirFresh
        air_fresh = AirFresh(host, token)
        device = XiaomiAirFreshD(name, air_fresh, model, unique_id)
    else:
        _LOGGER.error(
            'This custom components only support Mijia Airfresh t2017 '
            'and provide the following data: %s', model)
        return False

    hass.data[DATA_KEY][host] = device
    async_add_entities([device], update_before_add=True)

class AirFreshDStatus:
    """Container for status reports from the air fresh."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data

    @property
    def power(self) -> bool:
        """Power state."""
        return self.data["power"]

    @property
    def ptc_on(self) -> bool:
        """PTC Power state"""
        return self.data["ptc_on"]

    @property
    def is_on(self) -> bool:
        """Return True if device is on."""
        return self.power == True

    @property
    def pm25(self) -> int:
        """Air quality index."""
        return self.data["pm25"]

    @property
    def co2(self) -> int:
        """Carbon dioxide."""
        return self.data["co2"]

    @property
    def mode(self) -> OperationMode:
        """Current operation mode."""
        return OperationMode(self.data["mode"])

    @property
    def temperature_outside(self) -> int:
        """Outside Temperature"""
        return self.data["temperature_outside"]

    @property
    def favourite_speed(self) -> int:
        """Favourite Speed"""
        return self.data["favourite_speed"]

    @property
    def control_speed(self) -> int:
        """Control Speed"""
        return self.data["control_speed"]

    @property
    def filter_intermediate(self) -> int:
        """Filter of Intermediate Dead"""
        return self.data["filter_intermediate"]

    @property
    def filter_inter_day(self) -> int:
        return self.data["filter_inter_day"]

    @property
    def filter_efficient(self) -> int:
        return self.data["filter_efficient"]

    @property
    def filter_effi_day(self) -> int:
        return self.data["filter_effi_day"]

    @property
    def ptc_level(self) -> OperationPTCLevel:
        return OperationPTCLevel(self.data["ptc_level"])

    @property
    def ptc_status(self) -> bool:
        return self.data["ptc_status"]

    @property
    def child_lock(self) -> bool:
        return self.data["child_lock"]

    @property
    def sound(self) -> bool:
        return self.data["sound"]

    @property
    def display(self) -> bool:
        return self.data["display"]

    @property
    def screen_direction(self) -> DisplayOrientation:
        return DisplayOrientation(self.data["screen_direction"])

    def __repr__(self) -> str:
        s = "<AirFreshStatus power=%s, " \
            "pm25=%s, " \
            "co2=%s, " \
            "mode=%s>" % \
            (self.power,
             self.pm25,
             self.co2,
             self.mode)
        return s

    def __json__(self):
        return self.data


class XiaomiAirFreshD(FanEntity):
    """Representation of a generic Xiaomi device."""

    def __init__(self, name, device, model, unique_id):
        """Initialize the generic Xiaomi device."""
        self._name = name
        self._device = device
        self._model = model
        self._unique_id = unique_id

        self._available = False
        self._state = None
        self._state_attrs = {
            ATTR_MODEL: self._model,
        }
        self._skip_update = False

        self._device_features = FEATURE_FLAGS_DAIRFRESH
        self._available_attributes = AVAILABLE_ATTRIBUTES_AIRFRESH
        self._speed_list = OPERATION_MODES_AIRFRESH
        self._ptc_list = OPERATION_LEVELS_PTC
        self._state_attrs.update(
            {attribute: None for attribute in self._available_attributes})
  
    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_SET_SPEED

    @property
    def should_poll(self):
        """Poll the device."""
        return True

    @property
    def unique_id(self):
        """Return an unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def available(self):
        """Return true when state is known."""
        return self._available

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return self._speed_list

    @property
    def speed(self):
        """Return the current speed."""
        if self._state:
            return OperationMode(self._state_attrs[ATTR_MODE]).name

        return None

    @property
    def ptc_list(self) -> list:
        """Get the list of available ptc levels."""
        return self._ptc_list

    @property
    def ptc_level(self):
        if self._state:
            return OperationPTCLevel(self._state_attrs[ATTR_PTCLEVEL]).name

        return None

    @staticmethod
    def _extract_value_from_attribute(state, attribute):
        value = getattr(state, attribute)
        if isinstance(value, Enum):
            return value.value

        return value

    def get_status(self):
        properties = ["power", "pm25", "co2", "mode", "temperature_outside", 
            "favourite_speed", "control_speed", "filter_intermediate", "filter_inter_day",
            "filter_efficient", "filter_effi_day", "ptc_on", "ptc_level", "ptc_status",
            "sound", "display", "screen_direction"]

        # A single request is limited to 16 properties. Therefore the
        # properties are divided into multiple requests
        _props = properties.copy()
        values = []
        while _props:
            values.extend(self._device.send("get_prop", _props[:4]))
            _props[:] = _props[4:]

        properties_count = len(properties)
        values_count = len(values)
        if properties_count != values_count:
            _LOGGER.debug(
                "Count (%s) of requested properties does not match the "
                "count (%s) of received values.",
                properties_count, values_count)
        return AirFreshDStatus(
            defaultdict(lambda: None, zip(properties, values)))

    async def async_update(self):
        """Fetch state from the device."""
        from miio import DeviceException

        # On state change the device doesn't provide the new state immediately.
        if self._skip_update:
            self._skip_update = False
            return

        try:
            state = await self.hass.async_add_executor_job(
                self.get_status)
            _LOGGER.debug("Got new state: %s", state)

            self._available = True
            self._state = state.is_on
            self._state_attrs.update(
                {key: self._extract_value_from_attribute(state, value) for
                 key, value in self._available_attributes.items()})

        except DeviceException as ex:
            self._available = False
            _LOGGER.error("Got exception while fetching the state: %s", ex)

    async def _try_command(self, mask_error, *args, **kwargs):
        """Call a miio device command handling error messages."""
        from miio import DeviceException
        try:
            result = await self.hass.async_add_executor_job(
                partial(self._device.send, *args, **kwargs))

            _LOGGER.debug("Response received from miio device: %s", result)

            return result == SUCCESS
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            self._available = False
            return False

    async def send_raw_cmd(self, mask_error, command, parameters):
        """Send a raw command to the device."""
        _LOGGER.debug("sending cmd %s %s", command, parameters)
        result = await self._try_command(mask_error, command, parameters)
        return result

    async def async_turn_on(self, speed: str = None,
                            **kwargs) -> None:
        """Turn the device on."""
        if speed:
            # If operation mode was set the device must not be turned on.
            result = await self.async_set_speed(speed)
        else:
            result = await self.send_raw_cmd("Turning the miio device on failed.", "set_power", [True])

        if result:
            self._state = True
            self._skip_update = True

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        result = await self.send_raw_cmd("Turning the miio device off failed.", "set_power", [False])

        if result:
            self._state = False
            self._skip_update = True

    async def async_set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        if self.supported_features & SUPPORT_SET_SPEED == 0:
            return

        _LOGGER.debug("Setting the operation mode to: %s", speed)
        if  OperationMode[speed.title()].value == 'off':
            await self.async_turn_off()
        else:
            await self.send_raw_cmd(
                "Setting operation mode of the miio device failed.",
                "set_mode", OperationMode[speed.title()].value)