import uvicorn
from fastapi import FastAPI
from datetime import datetime

from services.weather import get_real_weather
from services.finance import get_usd_rate

app = FastAPI(title="Smart Display Backend")

@app.get("/api/dashboard")
def get_dashboard_data():
    return {
        "time": datetime.now().strftime("%H:%M"),
        "weather": get_real_weather(),
        "usd": get_usd_rate(),
        "status": "Online"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)