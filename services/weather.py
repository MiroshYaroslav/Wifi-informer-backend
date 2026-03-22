import requests
from config import LATITUDE, LONGITUDE, CITY, TIMEOUT

OPEN_METEO_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}&current_weather=true"
)
WTTR_URL = f"https://wttr.in/{CITY}?format=j1"


def get_weather_emoji(code: int, is_day: int) -> str:
    if code == 0:
        return "☀️" if is_day else "🌙"
    if code in [1, 2, 3]:
        return "⛅" if is_day else "☁️"
    if code in [45, 48]:
        return "🌫️"
    if code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        return "🌧️"
    if code in [71, 73, 75, 77, 85, 86]:
        return "❄️"
    if code in [95, 96, 99]:
        return "⛈️"
    return "🌡️"


def format_temperature(temp: float) -> str:
    return f"+{temp:.0f}°C" if temp > 0 else f"{temp:.0f}°C"


def get_open_meteo_weather(session: requests.Session) -> str:
    response = session.get(OPEN_METEO_URL, timeout=TIMEOUT)
    response.raise_for_status()

    current = response.json()["current_weather"]
    temp = float(current["temperature"])
    code = int(current["weathercode"])
    is_day = int(current.get("is_day", 1))

    return f"{CITY}\n{format_temperature(temp)}{get_weather_emoji(code, is_day)}"


def get_wttr_weather(session: requests.Session) -> str:
    response = session.get(WTTR_URL, timeout=TIMEOUT)
    response.raise_for_status()

    temp = float(response.json()["current_condition"][0]["temp_C"])
    return f"{CITY}\n{format_temperature(temp)}☁️"


def get_real_weather(session: requests.Session) -> str:
    try:
        return get_open_meteo_weather(session)
    except Exception as error:
        print(f"[Error Open-Meteo]: {error}. Trying wttr.in...")

    try:
        return get_wttr_weather(session)
    except Exception as error:
        print(f"[Error wttr.in]: {error}. No more sources available.")
        return f"{CITY}\nN/A"