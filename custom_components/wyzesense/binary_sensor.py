import logging
import voluptuous as vol
import json
import os
from os import path
from retry import retry
import subprocess
import asyncio

from homeassistant.const import (
    CONF_FILENAME, CONF_DEVICE, EVENT_HOMEASSISTANT_STOP, STATE_ON, STATE_OFF,
    ATTR_BATTERY_LEVEL, ATTR_STATE, ATTR_DEVICE_CLASS
)
from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA, BinarySensorEntity
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.storage import Store
import homeassistant.helpers.config_validation as cv
from homeassistant.components.persistent_notification import async_create as notify_create

DOMAIN = "wyzesense"
STORAGE_KEY = "wyzesense"
STORAGE_VERSION = 1
_LOGGER = logging.getLogger(__name__)

ATTR_MAC = "mac"
ATTR_RSSI = "rssi"
ATTR_AVAILABLE = "available"
CONF_INITIAL_STATE = "initial_state"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DEVICE, default="auto"): cv.string,
    vol.Optional(CONF_INITIAL_STATE, default={}): vol.Schema({cv.string: vol.In(["on", "off"])}),
})

SERVICE_SCAN = 'scan'
SERVICE_REMOVE = 'remove'

SERVICE_SCAN_SCHEMA = vol.Schema({})
SERVICE_REMOVE_SCHEMA = vol.Schema({vol.Required(ATTR_MAC): cv.string})

async def async_get_storage(hass):
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    storage = await store.async_load()
    if not storage:
        _LOGGER.debug("No existing storage found, initializing new storage.")
        storage = []
    return storage

async def async_set_storage(hass, data):
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_save(data)
    _LOGGER.debug("Storage successfully saved.")

def find_dongle():
    df = subprocess.check_output(["ls", "-la", "/sys/class/hidraw"]).decode('utf-8').lower()
    for l in df.split('\n'):
        if "e024" in l and "1a86" in l:
            for w in l.split(' '):
                if "hidraw" in w:
                    return f"/dev/{w}"
    return None

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async def setup():
        storage = await async_get_storage(hass)
        if not storage:
            _LOGGER.debug("Initializing storage for the first time.")
            await async_set_storage(hass, storage)

        device_path = config[CONF_DEVICE]
        if device_path.lower() == 'auto':
            device_path = find_dongle()
            if not device_path:
                _LOGGER.error("No WyzeSense dongle found.")
                return

        _LOGGER.debug("Attempting to open connection to hub at %s", device_path)

        forced_initial_states = config[CONF_INITIAL_STATE]
        entities = {}

        try:
            from .wyzesense_custom import Open
            ws = await hass.async_add_executor_job(Open, device_path, lambda ws, event: on_event(hass, async_add_entities, storage, ws, event, entities))
        except Exception as e:
            _LOGGER.error(f"Failed to connect to WyzeSense hub: {e}")
            return

        sensors = await async_get_storage(hass)
        for mac in sensors:
            data = {
                ATTR_AVAILABLE: False,
                ATTR_MAC: mac,
                ATTR_STATE: 0,
            }
            new_entity = WyzeSensor(data, hass=hass, should_restore=True)
            entities[mac] = new_entity
            async_add_entities([new_entity])

        async def async_on_scan(call):
            try:
                try:
                    result = await asyncio.wait_for(hass.async_add_executor_job(ws.Scan), timeout=60)
                except asyncio.TimeoutError:
                    _LOGGER.warning("Timeout while scanning for new WyzeSense sensors.")
                    return

                if result:
                    mac, sensor_type, version = result
                    if not mac or len(mac) != 8:
                        _LOGGER.warning(f"Invalid sensor MAC detected during scan: {mac}")
                        return

                    _LOGGER.info(f"Sensor found: MAC={mac}, Type={sensor_type}, Version={version}")

                    # Mostrar notificación usando contexto real de Home Assistant
                    hass.async_create_task(
                        hass.services.async_call(
                            "persistent_notification",
                            "create",
                            {
                                "message": f"Sensor detected: MAC={mac}, Type={sensor_type}",
                                "title": DOMAIN
                            }
                        )
                    )

                    # Prevenir duplicados por unique_id
                    if mac in entities:
                        _LOGGER.info(f"Sensor {mac} ya registrado en memoria.")
                        return

                    entity_registry = await hass.helpers.entity_registry.async_get_registry()
                    unique_id = mac
                    existing_entity = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
                    if existing_entity:
                        _LOGGER.info(f"Entity with MAC {mac} ya existe en el registro. Saltando creación.")
                        return

                    storage = await async_get_storage(hass)
                    if mac not in storage:
                        storage.append(mac)
                        await async_set_storage(hass, storage)

                    device_class = "motion" if sensor_type in [0x02, 0x0F] else "door"
                    new_entity = WyzeSensor({
                        ATTR_AVAILABLE: True,
                        ATTR_MAC: mac,
                        ATTR_STATE: 0,
                        ATTR_DEVICE_CLASS: device_class,
                    }, hass=hass, should_restore=True)

                    async_add_entities([new_entity], True)
                    entities[mac] = new_entity

                else:
                    _LOGGER.warning("Scan completed but no sensor was found.")

            except Exception as e:
                _LOGGER.exception("Unexpected error during wyzesense.scan service call: %s", e)

        async def async_on_shutdown(event):
            _LOGGER.debug("Closing connection to hub")
            ws.Stop()




        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_on_shutdown)
        hass.services.async_register(DOMAIN, SERVICE_SCAN, async_on_scan, schema=SERVICE_SCAN_SCHEMA)

    hass.async_create_task(setup())

def on_event(hass, async_add_entities, storage, ws, event, entities):
    if event.Type == 'state':
        sensor_type, sensor_state, sensor_battery, sensor_signal = event.Data
        if not event.MAC or len(event.MAC) != 8:
            _LOGGER.warning("Sensor with invalid MAC detected: %s", event.MAC)
            return

        device_class = "motion" if sensor_type in ["motion", 0x02, 0x0F] else "door"
        state = 1 if sensor_state in ["open", "active"] else 0

        data = {
            ATTR_AVAILABLE: True,
            ATTR_MAC: event.MAC,
            ATTR_STATE: state,
            ATTR_DEVICE_CLASS: device_class,
            ATTR_RSSI: sensor_signal * -1,
            ATTR_BATTERY_LEVEL: sensor_battery,
        }

        if event.MAC in entities:
            entities[event.MAC]._data.update(data)
            hass.loop.call_soon_threadsafe(entities[event.MAC].async_schedule_update_ha_state)
        else:
            new_entity = WyzeSensor(data, hass=hass, should_restore=True)
            def add_entity():
                async_add_entities([new_entity])
                entities[event.MAC] = new_entity
            hass.loop.call_soon_threadsafe(add_entity)
            hass.loop.call_soon_threadsafe(new_entity.async_schedule_update_ha_state)

class WyzeSensor(BinarySensorEntity, RestoreEntity):
    def __init__(self, data, hass=None, should_restore=False):
        self._data = data
        self._should_restore = should_restore
        self.hass = hass

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self._should_restore:
            last_state = await self.async_get_last_state()
            if last_state:
                self._data[ATTR_STATE] = 1 if last_state.state == "on" else 0
                self._data[ATTR_AVAILABLE] = True
                self.async_write_ha_state()

    @property
    def unique_id(self):
        return self._data[ATTR_MAC]

    @property
    def is_on(self):
        return self._data[ATTR_STATE]

    @property
    def device_class(self):
        return self._data.get(ATTR_DEVICE_CLASS)

    @property
    def extra_state_attributes(self):
        attributes = self._data.copy()
        attributes.pop(ATTR_STATE, None)
        return attributes