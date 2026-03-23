import time
import uvicorn
import paho.mqtt.client as mqtt
from fastapi import FastAPI
from pydantic import BaseModel

from services.finance import get_exchange_rates
from services.weather import get_real_weather
from services.fuel import get_fuel_prices
from services.smarthome import get_switch_state, toggle_switch

app = FastAPI(title="Smart Display Backend")

# --- MQTT SETUP ---
MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
MQTT_TOPIC_STATE = "smart/dashboard/state"
MQTT_TOPIC_TRIGGER = "smart/ha/trigger"

mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC_TRIGGER)

def on_message(client, userdata, msg):
    if msg.topic == MQTT_TOPIC_TRIGGER:
        print("[MQTT] HA state changed! Broadcasting new state...")
        new_state = get_full_dashboard_state()
        broadcast_data(new_state)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"[MQTT] Error connecting to broker: {e}")

# --- MODELS ---
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

# --- CACHE ---
class Cache:
    weather_data: str = "Loading..."
    usd_data: str = "N/A"
    eur_data: str = "N/A"
    fuel_data: str = "Loading..."
    last_updated: float = 0.0
    TTL_SECONDS: int = 900

# --- LOGIC ---
def broadcast_data(data: DashboardResponse):
    try:
        payload = data.model_dump_json()
        mqtt_client.publish(MQTT_TOPIC_STATE, payload, retain=True)
        print("[MQTT] Broadcast sent to ESP32")
    except Exception as e:
        print(f"[MQTT] Publish error: {e}")

def get_full_dashboard_state() -> DashboardResponse:
    current_time = time.time()

    if current_time - Cache.last_updated > Cache.TTL_SECONDS:
        print("[Cache] Data expired. Fetching new data...")
        import requests
        with requests.Session() as session:
            Cache.weather_data = get_real_weather(session)
            Cache.usd_data, Cache.eur_data = get_exchange_rates(session)
            Cache.fuel_data = get_fuel_prices(session)
        Cache.last_updated = current_time

    current_smarthome_state = SmartHomeStatus(
        komp_iuter=get_switch_state("input_boolean.komp_iuter"),
        svitlo=get_switch_state("input_boolean.svitlo")
    )

    return DashboardResponse(
        weather=Cache.weather_data,
        usd=Cache.usd_data,
        eur=Cache.eur_data,
        fuel=Cache.fuel_data,
        status="Online" if Cache.usd_data != "N/A" else "Degraded",
        smarthome=current_smarthome_state
    )

# --- ENDPOINTS ---
@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard_api():
    return get_full_dashboard_state()

@app.post("/api/smarthome/toggle")
def toggle_smarthome_device(device: str):
    if device == "komp_iuter":
        entity = "input_boolean.komp_iuter"
    elif device == "svitlo":
        entity = "input_boolean.svitlo"
    else:
        return {"error": "Unknown device"}

    toggle_switch(entity)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)