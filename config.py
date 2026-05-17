import os
from dotenv import load_dotenv

load_dotenv()

LATITUDE = 49.8383
LONGITUDE = 24.0232
CITY = "Lviv"
TIMEOUT = 3.0

HA_URL = os.getenv("HA_URL", "http://homeassistant:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "")
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
OWM_API_KEY = os.getenv("OWM_API_KEY", "")