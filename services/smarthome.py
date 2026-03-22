import requests
from config import HA_URL, HA_TOKEN

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

def get_switch_state(entity_id: str) -> bool:
    url = f"{HA_URL}/api/states/{entity_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=3)
        response.raise_for_status()
        return response.json().get("state") == "on"
    except Exception as e:
        print(f"[HA Error] Failed to get state for {entity_id}: {e}")
        return False

def toggle_switch(entity_id: str) -> bool:
    url = f"{HA_URL}/api/services/input_boolean/toggle"
    payload = {"entity_id": entity_id}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=3)
        response.raise_for_status()
        return get_switch_state(entity_id)
    except Exception as e:
        print(f"[HA Error] Failed to toggle {entity_id}: {e}")
        return False