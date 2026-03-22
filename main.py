import time
import requests
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from services.finance import get_exchange_rates
from services.weather import get_real_weather
from services.fuel import get_fuel_prices

app = FastAPI(title="Smart Display Backend")


class DashboardResponse(BaseModel):
    weather: str
    usd: str
    eur: str
    fuel: str
    status: str


class Cache:
    weather_data: str = "Loading..."
    usd_data: str = "N/A"
    eur_data: str = "N/A"
    fuel_data: str = "Loading..."
    last_updated: float = 0.0
    TTL_SECONDS: int = 900


@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard_data() -> DashboardResponse:
    current_time = time.time()

    if current_time - Cache.last_updated > Cache.TTL_SECONDS:
        print("[Cache] Data expired. Fetching new data...")
        with requests.Session() as session:
            Cache.weather_data = get_real_weather(session)
            Cache.usd_data, Cache.eur_data = get_exchange_rates(session)
            Cache.fuel_data = get_fuel_prices(session)

        Cache.last_updated = current_time

    return DashboardResponse(
        weather=Cache.weather_data,
        usd=Cache.usd_data,
        eur=Cache.eur_data,
        fuel=Cache.fuel_data,
        status="Online" if Cache.usd_data != "N/A" else "Degraded",
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)