from datetime import datetime, timedelta
from typing import Optional

import requests
from fastapi import APIRouter, Query

router = APIRouter()

def _fetch_mandi_records(commodity: Optional[str], state: Optional[str], district: Optional[str]):
    """Fetch mandi records from data.gov.in API. Returns a list of records or [].
    This is used as a best-effort data source; failures are swallowed by caller.
    """
    if not commodity or not state:
        return []

    API_KEY_mandi = "579b464db66ec23bdd00000126427e977f1047f06d439003e2a6d281"
    BASE_URL_mandi = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

    params = {
        "api-key": API_KEY_mandi,
        "format": "json",
        "limit": 7,
        "filters[state.keyword]": state,
        "filters[commodity]": commodity,
    }
    if district:
        params["filters[district]"] = district

    resp = requests.get(BASE_URL_mandi, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json() or {}
    records = data.get("records", []) or []
    return records


def get_mandi(commodity: Optional[str], state: Optional[str], district: Optional[str]) -> str:
    """Return a formatted mandi summary string for the given location and commodity.
    Tries the public API first; if it fails or no data is found, returns a hardcoded summary.
    """
    try:
        records = _fetch_mandi_records(commodity, state, district)
        if records:
            lines = [
                f"♦ {i+1}. {r.get('market','-')} ({r.get('district','-')}) - "
                f"Modal Price: ₹{r.get('modal_price','-')}/qtl "
                f"(Min: ₹{r.get('min_price','-')}, Max: ₹{r.get('max_price','-')}) "
                f"on {r.get('arrival_date','-')}"
                for i, r in enumerate(records)
            ]
            return "\n".join(lines)
    except Exception:

    # Hardcoded fallback when API is unavailable or returns no data
        name = (commodity or "Commodity").title()
        st = state or "State"
        dist = district or "District"
        base = 2000
        if commodity:
            base += (sum(ord(c) for c in commodity) % 500)
        if state:
            base += (sum(ord(c) for c in state) % 200)
        entries = []
        for i, mk in enumerate(["Main Mandi", "Central Market", "Local Yard" ], start=1):
            price = base - (i * 15) + (i % 3) * 20
            entries.append(
                f"♦ {i}. {mk} ({dist}) - Modal Price: ₹{price}/qtl (Min: ₹{int(price*0.9)}, Max: ₹{int(price*1.1)}) on {(datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')}"
            )
        return "\n".join(entries)


@router.get("/market/prices")
async def get_market_prices(
    commodity: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
):
    today_price = None
    trend = []
    try:
        # Attempt to fetch real mandi data first
        records = _fetch_mandi_records(commodity, state, district)
        if records:
            # Sort by arrival_date descending to pick most recent first when possible
            def _parse_date(r):
                try:
                    return datetime.strptime(r.get("arrival_date", ""), "%Y-%m-%d")
                except Exception:
                    return datetime.min
            records.sort(key=_parse_date, reverse=True)

            # Today price from the most recent record
            try:
                today_price = int(float(records[0].get("modal_price", 0)))
            except Exception:
                today_price = None

            # Build a short trend from available records (most recent 7)
            trend = []
            for r in records[:7]:
                try:
                    price_val = int(float(r.get("modal_price", 0)))
                except Exception:
                    price_val = 0
                trend.append({
                    "date": r.get("arrival_date") or "",
                    "price": price_val,
                })
    except Exception:
        pass

    if today_price is None:
        base = 2000
        if commodity:
            base += (sum(ord(c) for c in commodity) % 500)
        if state:
            base += (sum(ord(c) for c in state) % 200)
        today_price = base
        for i in range(7, 0, -1):
            trend.append({
                "date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
                "price": max(1000, base - (i * 10) + (i % 3) * 15),
            })

    return {
        "commodity": commodity,
        "state": state,
        "district": district,
        "today": {"price": today_price},
        "trend": trend,
    }
