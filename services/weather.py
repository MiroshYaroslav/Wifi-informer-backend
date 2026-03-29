import requests
from config import LATITUDE, LONGITUDE, CITY, TIMEOUT

OWM_API_KEY = "9f2e7f0f270fb18873989eab0ed2913b"

OWM_URL = (
    f"https://api.openweathermap.org/data/2.5/weather"
    f"?lat={LATITUDE}&lon={LONGITUDE}&appid={OWM_API_KEY}&units=metric"
)

OPEN_METEO_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}&current_weather=true"
)

def format_temperature(temp: float) -> str:
    return f"+{temp:.0f}°C" if temp > 0 else f"{temp:.0f}°C"

def get_owm_emoji(code: int, icon_id: str) -> str:
    is_day = "d" in icon_id

    if code == 800:
        emoji = "☀️" if is_day else "🌙"
    elif code in [801, 802]:
        emoji = "⛅" if is_day else "☁️"
    elif code in [803, 804]:
        emoji = "☁️"
    elif 700 <= code < 800:
        emoji = "🌫️"
    elif 600 <= code < 700:
        emoji = "❄️"
    elif 300 <= code < 600:
        emoji = "🌧️"
    elif 200 <= code < 300:
        emoji = "⛈️"
    else:
        emoji = "🌡️"

    return emoji.replace("\ufe0f", "")

def get_owm_weather(session: requests.Session) -> str:
    if not OWM_API_KEY or OWM_API_KEY == "ТВІЙ_КЛЮЧ_ТУТ":
        raise ValueError("No OWM API key configured")

    response = session.get(OWM_URL, timeout=TIMEOUT)
    response.raise_for_status()

    data = response.json()
    temp = float(data["main"]["temp"])
    code = int(data["weather"][0]["id"])
    icon_id = data["weather"][0]["icon"]

    return f"{CITY}\n{format_temperature(temp)}{get_owm_emoji(code, icon_id)}"

def get_open_meteo_emoji(code: int, is_day: int) -> str:
    if code == 0:
        emoji = "☀️" if is_day else "🌙"
    elif code in [1, 2]:
        emoji = "⛅" if is_day else "☁️"
    elif code == 3:
        emoji = "☁️"
    elif code in [45, 48]:
        emoji = "🌫️"
    elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        emoji = "🌧️"
    elif code in [71, 73, 75, 77, 85, 86]:
        emoji = "❄️"
    elif code in [95, 96, 99]:
        emoji = "⛈️"
    else:
        emoji = "☁️"

    return emoji.replace("\ufe0f", "")

def get_open_meteo_weather(session: requests.Session) -> str:
    response = session.get(OPEN_METEO_URL, timeout=TIMEOUT)
    response.raise_for_status()

    current = response.json()["current_weather"]
    temp = float(current["temperature"])
    code = int(current["weathercode"])
    is_day = int(current.get("is_day", 1))

    return f"{CITY}\n{format_temperature(temp)}{get_open_meteo_emoji(code, is_day)}"

def get_real_weather(session: requests.Session) -> str:
    try:
        return get_owm_weather(session)
    except Exception as error:
        print(f"[OWM Skipped/Error]: {error}. Trying Open-Meteo...")

    try:
        return get_open_meteo_weather(session)
    except Exception as error:
        print(f"[Error Open-Meteo]: {error}. No more sources available.")
        return f"{CITY}\nN/A"