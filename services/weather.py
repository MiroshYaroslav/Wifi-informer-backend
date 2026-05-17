import httpx
import logging
from config import LATITUDE, LONGITUDE, CITY, TIMEOUT, OWM_API_KEY

logger = logging.getLogger(__name__)

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
        return "☀️" if is_day else "🌙"
    elif code in [801, 802]:
        return "⛅" if is_day else "☁️"
    elif code in [803, 804]:
        return "☁️"
    elif 700 <= code < 800:
        return "🌫️"
    elif 600 <= code < 700:
        return "❄️"
    elif 300 <= code < 600:
        return "🌧️"
    elif 200 <= code < 300:
        return "⛈️"
    return "🌡️"


def get_open_meteo_emoji(code: int, is_day: int) -> str:
    if code == 0:
        return "☀️" if is_day else "🌙"
    elif code in [1, 2]:
        return "⛅" if is_day else "☁️"
    elif code == 3:
        return "☁️"
    elif code in [45, 48]:
        return "🌫️"
    elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        return "🌧️"
    elif code in [71, 73, 75, 77, 85, 86]:
        return "❄️"
    elif code in [95, 96, 99]:
        return "⛈️"
    return "☁️"


async def get_owm_weather() -> str:
    if not OWM_API_KEY:
        raise ValueError("No OWM API key configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(OWM_URL, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

    temp = float(data["main"]["temp"])
    code = int(data["weather"][0]["id"])
    icon_id = data["weather"][0]["icon"]

    return f"{CITY}\n{format_temperature(temp)}{get_owm_emoji(code, icon_id).replace(chr(65039), '')}"


async def get_open_meteo_weather() -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(OPEN_METEO_URL, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()["current_weather"]

    temp = float(data["temperature"])
    code = int(data["weathercode"])
    is_day = int(data.get("is_day", 1))

    return f"{CITY}\n{format_temperature(temp)}{get_open_meteo_emoji(code, is_day).replace(chr(65039), '')}"


async def get_real_weather() -> str:
    try:
        return await get_owm_weather()
    except Exception as error:
        logger.warning(f"OWM failed: {error}. Trying Open-Meteo...")
        try:
            return await get_open_meteo_weather()
        except Exception as error:
            logger.error(f"Open-Meteo failed: {error}.")
            return f"{CITY}\nN/A"