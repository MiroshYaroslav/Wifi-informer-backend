from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from config import TIMEZONE
from services.finance import get_usd_rate
from services.weather import get_real_weather

app = FastAPI(title="Smart Display Backend")


class DashboardResponse(BaseModel):
    time: str
    weather: str
    usd: str
    status: str


def get_dashboard_status(weather: str, usd: str) -> str:
    if weather == "N/A" or usd == "N/A":
        return "Degraded"
    return "Online"


@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard_data() -> DashboardResponse:
    with requests.Session() as session:
        weather = get_real_weather(session)
        usd = get_usd_rate(session)

    current_time = datetime.now(ZoneInfo(TIMEZONE)).strftime("%H:%M")
    status = get_dashboard_status(weather, usd)

    return DashboardResponse(
        time=current_time,
        weather=weather,
        usd=usd,
        status=status,
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)