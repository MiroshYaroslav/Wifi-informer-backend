import asyncio
import socket
import json
import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager
from typing import List, Optional

import paho.mqtt.client as mqtt
from fastapi import FastAPI, Response
from pydantic import BaseModel
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

from config import MQTT_BROKER, MQTT_PORT
from services.weather import get_real_weather
from services.smarthome import perform_action, get_controllable_entities, get_camera_log

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

UDP_PORT = 5555
DISCOVERY_MSG = "DISCOVER_SMART_DASHBOARD"
REPLY_MSG = b"BACKEND_HERE"

MQTT_TOPIC_STATE = "smart/dashboard/state"
MQTT_TOPIC_TRIGGER = "smart/ha/trigger"
MQTT_TOPIC_HEARTBEAT = "smart/dashboard/heartbeat"
MQTT_TOPIC_COMMAND = "smart/dashboard/command"
MQTT_TOPIC_TELEMETRY = "smart/dashboard/telemetry"  # Новий топік для читання

# --- МЕТРИКИ ДЛЯ PROMETHEUS ---
esp_rssi_gauge = Gauge('esp_wifi_rssi_dbm', 'WiFi Signal Strength (dBm)')
esp_uptime_gauge = Gauge('esp_uptime_seconds', 'ESP32 Uptime (seconds)')
esp_heap_gauge = Gauge('esp_free_heap_bytes', 'ESP32 Free Heap Memory (bytes)')

main_loop: Optional[asyncio.AbstractEventLoop] = None


class Cache:
    weather_data: str = "Loading..."
    last_weather_update: float = 0.0
    WEATHER_TTL: int = 600
    camera_history: list = []
    last_raw_cam_log: str = None
    lock = asyncio.Lock()


class ControllableDevice(BaseModel):
    entity_id: str
    friendly_name: str
    state: bool
    domain: str
    ui_type: str
    value: int = 0


class DashboardResponse(BaseModel):
    weather: str
    status: str
    camera_log: str
    controllable_devices: List[ControllableDevice]


mqtt_client = mqtt.Client()


async def publish_state_async():
    data = await get_full_dashboard_state()
    try:
        mqtt_client.publish(MQTT_TOPIC_STATE, data.model_dump_json(), retain=True)
    except Exception as e:
        logger.error(f"MQTT publish failed: {e}")


def on_connect(_client, _userdata, _flags, _rc):
    logger.info("Connected to MQTT broker")
    _client.subscribe(MQTT_TOPIC_TRIGGER)
    _client.subscribe(MQTT_TOPIC_COMMAND)
    _client.subscribe(MQTT_TOPIC_TELEMETRY)  # Підписуємося на телеметрію
    if main_loop is not None and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(publish_state_async(), main_loop)


def on_message(_client, _userdata, msg):
    if main_loop is None or not main_loop.is_running():
        return

    if msg.topic == MQTT_TOPIC_TRIGGER:
        asyncio.run_coroutine_threadsafe(publish_state_async(), main_loop)

    elif msg.topic == MQTT_TOPIC_COMMAND:
        try:
            payload = json.loads(msg.payload.decode())
            entity_id = payload.get("entity_id")
            action = payload.get("action", "toggle")
            value = payload.get("value", 0)
            if entity_id:
                asyncio.run_coroutine_threadsafe(handle_mqtt_command(entity_id, action, value), main_loop)
        except Exception as e:
            logger.error(f"Command parsing failed: {e}")

    elif msg.topic == MQTT_TOPIC_TELEMETRY:
        # Ловимо телеметрію з екрана і записуємо в Prometheus
        try:
            payload = json.loads(msg.payload.decode())
            if "rssi" in payload:
                esp_rssi_gauge.set(payload["rssi"])
            if "uptime" in payload:
                esp_uptime_gauge.set(payload["uptime"])
            if "free_heap" in payload:
                esp_heap_gauge.set(payload["free_heap"])
        except Exception as e:
            logger.error(f"Telemetry parsing failed: {e}")


mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


async def handle_mqtt_command(entity_id: str, action: str, value: int):
    success = await perform_action(entity_id, action, value)
    if success:
        await asyncio.sleep(1.0)
        await publish_state_async()


async def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.setblocking(False)
    while True:
        try:
            if main_loop is not None:
                data, addr = await main_loop.sock_recvfrom(sock, 1024)
                if data.decode('utf-8', errors='ignore').strip() == DISCOVERY_MSG:
                    await main_loop.sock_sendto(sock, REPLY_MSG, addr)
        except Exception as e:
            logger.error(f"UDP error: {e}")
            await asyncio.sleep(0.5)


async def mqtt_connect_with_retry():
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            mqtt_client.loop_start()
            break
        except Exception as e:
            logger.warning(f"MQTT connect failed: {e}. Retrying in 5s...")
            await asyncio.sleep(5)


async def heartbeat_worker():
    while True:
        payload = {"backend": "ok", "ha_status": "Online"}
        try:
            mqtt_client.publish(MQTT_TOPIC_HEARTBEAT, json.dumps(payload), qos=0)
        except Exception as e:
            logger.debug(f"Heartbeat publish skip: {e}")
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    main_loop.create_task(udp_listener())
    main_loop.create_task(mqtt_connect_with_retry())
    main_loop.create_task(heartbeat_worker())
    yield
    mqtt_client.loop_stop()


app = FastAPI(title="Smart Display Backend", lifespan=lifespan)


async def get_full_dashboard_state() -> DashboardResponse:
    current_time = time.time()
    ha_status = "Online"
    controllable_devices = []
    formatted_history = "No events"
    try:
        devices_data = await get_controllable_entities()
        controllable_devices = [ControllableDevice(**device) for device in devices_data]
        raw_cam_log = await get_camera_log()
        async with Cache.lock:
            if Cache.last_raw_cam_log is None:
                Cache.last_raw_cam_log = raw_cam_log
                timestamp = datetime.now().strftime("%H:%M")
                Cache.camera_history = [f"[{timestamp}] {raw_cam_log}"]
            elif raw_cam_log != Cache.last_raw_cam_log:
                Cache.last_raw_cam_log = raw_cam_log
                timestamp = datetime.now().strftime("%H:%M")
                Cache.camera_history.insert(0, f"[{timestamp}] {raw_cam_log}")
                Cache.camera_history = Cache.camera_history[:4]
            formatted_history = "\n".join(Cache.camera_history)
    except Exception:
        ha_status = "HA_Offline"

    async with Cache.lock:
        if current_time - Cache.last_weather_update > Cache.WEATHER_TTL:
            try:
                Cache.weather_data = await get_real_weather()
                Cache.last_weather_update = current_time
            except Exception as e:
                logger.debug(f"Weather update failed: {e}")
        weather = Cache.weather_data

    return DashboardResponse(
        weather=weather,
        status=ha_status,
        camera_log=formatted_history,
        controllable_devices=controllable_devices
    )


@app.get("/api/dashboard", response_model=DashboardResponse)
async def get_dashboard_api():
    return await get_full_dashboard_state()


# Роут для збору метрик
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)