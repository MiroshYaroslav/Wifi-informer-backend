import httpx
import logging
from config import HA_URL, HA_TOKEN

logger = logging.getLogger(__name__)

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

async def get_camera_log() -> str:
    url = f"{HA_URL}/api/states/input_text.camera_log"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=HEADERS, timeout=2.0)
            if response.status_code == 200:
                return response.json().get("state", "No events")
        except httpx.RequestError:
            pass
    return "Connection error"

async def get_controllable_entities() -> list[dict]:
    url = f"{HA_URL}/api/states"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS, timeout=5.0)
        response.raise_for_status()
        states = response.json()

    led_brightness_fallback = 0
    for s in states:
        if s.get("entity_id") == "input_number.led_brightness_helper":
            try:
                led_brightness_fallback = int(float(s.get("state", 0)))
            except ValueError:
                pass
            break

    controllable = []
    for state in states:
        entity_id = state.get("entity_id", "")
        if "_helper" in entity_id:
            continue

        domain = entity_id.split(".")[0] if "." in entity_id else ""
        if domain in ["switch", "light", "input_boolean", "cover"]:
            ui_type = "toggle"
            if domain == "light":
                ui_type = "slider"
            elif domain == "cover":
                ui_type = "button"

            friendly_name = str(state.get("attributes", {}).get("friendly_name", entity_id))
            is_active = state.get("state") in ["on", "open", "opening"]

            current_value = 0
            if is_active and domain == "light":
                brightness = state.get("attributes", {}).get("brightness")
                if brightness is not None:
                    current_value = round((float(brightness) / 255.0) * 100)
                else:
                    current_value = round((led_brightness_fallback / 255.0) * 100)

            controllable.append({
                "entity_id": entity_id,
                "friendly_name": friendly_name,
                "state": is_active,
                "domain": domain,
                "ui_type": ui_type,
                "value": current_value
            })

    controllable.sort(key=lambda x: x['friendly_name'])
    return controllable[:15]

async def perform_action(entity_id: str, action: str, value: int = 0) -> bool:
    domain = entity_id.split(".")[0]
    service = "toggle"
    payload = {"entity_id": entity_id}

    if action == "slider" and domain == "light":
        if value > 0:
            service = "turn_on"
            payload["brightness_pct"] = value
        else:
            service = "turn_off"

    url = f"{HA_URL}/api/services/{domain}/{service}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=HEADERS, json=payload, timeout=3.0)
            response.raise_for_status()
            return True
        except httpx.RequestError as e:
            logger.error(f"HA Action failed: {e}")
            return False