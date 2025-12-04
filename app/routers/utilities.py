from typing import Any, Dict

import requests
from fastapi import APIRouter, Body

from ..utils.ai import generate_text

router = APIRouter()


def _geocode(location: str) -> tuple[float, float] | None:
    try:
        # Open-Meteo geocoding API (no key)
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": location, "count": 1, "language": "en"}, timeout=10)
        j = r.json()
        if j.get("results"):
            it = j["results"][0]
            return float(it["latitude"]), float(it["longitude"])
    except Exception:
        return None
    return None


def _weather_for_location(location: str) -> Dict[str, Any]:
    coords = _geocode(location)
    if not coords:
        return {"error": "Location not found"}
    lat, lon = coords
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "relative_humidity_2m,temperature_2m",
                "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                "forecast_days": 1,
                "timezone": "auto",
            },
            timeout=10,
        )
        j = r.json()
        humidity = (j.get("hourly", {}).get("relative_humidity_2m") or [None])[0]
        tmax = (j.get("daily", {}).get("temperature_2m_max") or [None])[0]
        tmin = (j.get("daily", {}).get("temperature_2m_min") or [None])[0]
        forecast = f"Min {tmin}°C / Max {tmax}°C"
        return {"forecast": forecast, "humidity": humidity, "alerts": []}
    except Exception:
        return {"forecast": "Unavailable", "humidity": None, "alerts": []}


def _soil_insights(crop: str | None, soil_type: str | None) -> Dict[str, Any]:
    base = "Provide concise agronomy recommendations for crop and soil given."
    prompt = f"{base}\nCrop: {crop or '-'}\nSoil: {soil_type or '-'}\nReturn a short paragraph with recommendations and a separate fertilizer suggestion sentence."
    text = generate_text(prompt)
    return {"recommendations": text, "fertilizer": "Use balanced NPK as per local guidelines."}


def _outage_prediction(region: str | None) -> Dict[str, Any]:
    prompt = (
        "Based on general rural power conditions and weather risk, provide a short risk assessment (low/medium/high) for power outages in the region and a one-line note."
        f" Region: {region or '-'}"
    )
    text = generate_text(prompt)
    risk = "medium"
    if "high" in text.lower():
        risk = "high"
    elif "low" in text.lower():
        risk = "low"
    return {"risk": risk, "notes": text}


@router.post("/utilities/run")
async def run_utility(body: Dict[str, Any] = Body(...)):
    tool = body.get("tool")
    payload = body.get("payload") or {}
    if tool == "weather":
        return _weather_for_location(str(payload.get("location", "")))
    if tool == "soil":
        return _soil_insights(payload.get("crop"), payload.get("soilType"))
    if tool == "outage":
        return _outage_prediction(payload.get("region"))
    return {"error": "Unknown tool"}
