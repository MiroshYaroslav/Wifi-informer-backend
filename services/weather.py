import requests
from config import LATITUDE, LONGITUDE, CITY, TIMEOUT


def get_open_meteo() -> str:
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current_weather=true"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    temp = response.json()["current_weather"]["temperature"]
    return f"+{temp}°C" if temp > 0 else f"{temp}°C"


def get_wttr_weather() -> str:
    url = f"https://wttr.in/{CITY}?format=j1"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    temp = float(response.json()["current_condition"][0]["temp_C"])
    return f"+{temp}°C" if temp > 0 else f"{temp}°C"


def get_real_weather() -> str:
    try:
        return get_open_meteo()
    except Exception as e:
        print(f"[Error Open-Meteo]: {e}. Trying wttr.in...")

        try:
            return get_wttr_weather()
        except Exception as fallback_e:
            print(f"[Error wttr.in]: {fallback_e}. No more sources available.")
            return "N/A"