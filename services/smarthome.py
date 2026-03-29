import requests
from config import HA_URL, HA_TOKEN

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

def check_ha_connection() -> bool:
    url = f"{HA_URL}/api/"
    try:
        response = requests.get(url, headers=HEADERS, timeout=(0.5, 1.0))
        return response.status_code == 200
    except Exception:
        return False

def get_switch_state(entity_id: str) -> bool:
    url = f"{HA_URL}/api/states/{entity_id}"
    response = requests.get(url, headers=HEADERS, timeout=(0.5, 2.0))
    response.raise_for_status()
    return response.json().get("state") == "on"

def toggle_switch(entity_id: str) -> bool:
    url = f"{HA_URL}/api/services/input_boolean/toggle"
    payload = {"entity_id": entity_id}
    response = requests.post(url, headers=HEADERS, json=payload, timeout=(0.5, 2.0))
    response.raise_for_status()
    return get_switch_state(entity_id)