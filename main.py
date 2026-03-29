import time
import socket
import threading
import requests
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import uvicorn
import paho.mqtt.client as mqtt
from fastapi import FastAPI
from pydantic import BaseModel

from services.finance import get_exchange_rates
from services.weather import get_real_weather
from services.fuel import get_fuel_prices
from services.smarthome import get_switch_state, toggle_switch, check_ha_connection

UDP_PORT = 5555
DISCOVERY_MSG = "DISCOVER_SMART_DASHBOARD"
REPLY_MSG = b"BACKEND_HERE"

MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
MQTT_TOPIC_STATE = "smart/dashboard/state"
MQTT_TOPIC_TRIGGER = "smart/ha/trigger"
MQTT_TOPIC_HEARTBEAT = "smart/dashboard/heartbeat"

class Cache:
    weather_data: str = "Loading..."
    usd_data: str = "N/A"
    eur_data: str = "N/A"
    fuel_data: str = "Loading..."
    last_updated: float = 0.0
    TTL_SECONDS: int = 600
    lock = threading.Lock()

class SmartHomeStatus(BaseModel):
    komp_iuter: bool
    svitlo: bool

class DashboardResponse(BaseModel):
    weather: str
    usd: str
    eur: str
    fuel: str
    status: str
    smarthome: SmartHomeStatus

def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if data.decode('utf-8', errors='ignore').strip() == DISCOVERY_MSG:
                sock.sendto(REPLY_MSG, addr)
        except Exception:
            pass

executor = ThreadPoolExecutor(max_workers=4)
mqtt_client = mqtt.Client()

def publish_state_async():
    broadcast_data(get_full_dashboard_state())

def on_connect(client, userdata, flags, rc):
    client.subscribe(MQTT_TOPIC_TRIGGER)
    executor.submit(publish_state_async)

def on_message(client, userdata, msg):
    if msg.topic == MQTT_TOPIC_TRIGGER:
        executor.submit(publish_state_async)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def _mqtt_connect_with_retry():
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            return
        except Exception:
            time.sleep(5)

def heartbeat_worker():
    while True:
        ha_ok = check_ha_connection()
        payload = {
            "backend": "ok",
            "ha_status": "Online" if ha_ok else "HA_Offline"
        }
        try:
            mqtt_client.publish(MQTT_TOPIC_HEARTBEAT, json.dumps(payload), qos=0)
        except Exception:
            pass
        time.sleep(3)

@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=udp_listener, daemon=True).start()
    mqtt_client.loop_start()
    threading.Thread(target=_mqtt_connect_with_retry, daemon=True).start()
    threading.Thread(target=heartbeat_worker, daemon=True).start()
    yield
    executor.shutdown(wait=False)

app = FastAPI(title="Smart Display Backend", lifespan=lifespan)

def broadcast_data(data: DashboardResponse):
    try:
        mqtt_client.publish(MQTT_TOPIC_STATE, data.model_dump_json(), retain=True)
    except Exception:
        pass

def _fetch_ha_states() -> tuple[bool, bool, str]:
    with ThreadPoolExecutor(max_workers=2) as ha_executor:
        f_komp = ha_executor.submit(get_switch_state, "input_boolean.komp_iuter")
        f_svitlo = ha_executor.submit(get_switch_state, "input_boolean.svitlo")
        try:
            komp = f_komp.result(timeout=2.5)
            svitlo = f_svitlo.result(timeout=2.5)
            return komp, svitlo, "Online"
        except Exception:
            return False, False, "HA_Offline"

def get_full_dashboard_state() -> DashboardResponse:
    current_time = time.time()

    with Cache.lock:
        if current_time - Cache.last_updated > Cache.TTL_SECONDS:
            try:
                with requests.Session() as session:
                    Cache.weather_data = get_real_weather(session)
                    Cache.usd_data, Cache.eur_data = get_exchange_rates(session)
                    Cache.fuel_data = get_fuel_prices(session)
                Cache.last_updated = current_time
            except Exception:
                pass

    komp_state, svitlo_state, ha_status = _fetch_ha_states()

    return DashboardResponse(
        weather=Cache.weather_data,
        usd=Cache.usd_data,
        eur=Cache.eur_data,
        fuel=Cache.fuel_data,
        status=ha_status,
        smarthome=SmartHomeStatus(
            komp_iuter=komp_state,
            svitlo=svitlo_state
        )
    )

@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard_api():
    return get_full_dashboard_state()

@app.post("/api/smarthome/toggle")
def toggle_smarthome_device(device: str):
    device_map = {
        "komp_iuter": "input_boolean.komp_iuter",
        "svitlo": "input_boolean.svitlo"
    }

    entity = device_map.get(device)
    if not entity:
        return {"error": "Unknown device"}

    try:
        toggle_switch(entity)
        return {"status": "ok"}
    except Exception:
        return {"status": "error", "message": "HA is offline"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)