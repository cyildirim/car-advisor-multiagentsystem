"""
MOT History MCP Server
Wraps the DVSA MOT History API (new v1 API) as an MCP tool.

Requires:
  - MOT_API_KEY       (X-API-Key header)
  - MOT_CLIENT_ID     (Azure AD client ID for OAuth2)
  - MOT_CLIENT_SECRET (Azure AD client secret)
  - MOT_TENANT_ID     (Azure AD tenant ID)

Register at: https://documentation.history.mot.api.gov.uk/mot-history-api/register
"""

import os
import time
import httpx
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configure host and port for Cloud Run
port = int(os.getenv("PORT", "8000"))
host = "0.0.0.0" if os.getenv("PORT") else "127.0.0.1"

mcp = FastMCP("MOT History", host=host, port=port)

# ── Token cache ──────────────────────────────────────────────────────────────
_token_cache: dict = {"token": None, "expires_at": 0}

MOT_API_BASE = "https://history.mot.api.gov.uk"


def _get_access_token() -> str:
    """Fetch (or return cached) OAuth2 bearer token from Microsoft Entra ID."""
    if time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["token"]

    tenant_id     = os.environ["MOT_TENANT_ID"]
    client_id     = os.environ["MOT_CLIENT_ID"]
    client_secret = os.environ["MOT_CLIENT_SECRET"]

    resp = httpx.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
            "scope":         "https://tapi.dvsa.gov.uk/.default",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"]      = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"]
    return _token_cache["token"]


def _mot_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "X-API-Key":     os.environ["MOT_API_KEY"],
        "Accept":        "application/json",
    }


# ── MCP Tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def get_mot_history(registration: str) -> dict:
    """
    Fetch full MOT test history for a UK vehicle by registration plate.

    Returns vehicle details and a list of all MOT tests with:
    - pass/fail result
    - test date and expiry date
    - odometer reading
    - failure reasons (RFRs) and advisory notices

    Args:
        registration: UK vehicle registration number, e.g. "AB12CDE"
    """
    reg = registration.replace(" ", "").upper()
    url = f"{MOT_API_BASE}/v1/trade/vehicles/registration/{reg}"

    resp = httpx.get(url, headers=_mot_headers(), timeout=15)

    if resp.status_code == 404:
        return {"error": f"No MOT records found for registration '{reg}'"}
    if resp.status_code == 403:
        return {"error": "API key invalid or not authorised"}

    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def summarise_mot_risks(registration: str) -> dict:
    """
    Analyse MOT history for a vehicle and surface potential risk flags:
    - Number of failures in last 3 years
    - Recurring failure categories (brakes, emissions, tyres, lights, etc.)
    - Advisory notices that may indicate future failures
    - Mileage consistency check (flag if mileage drops between tests)
    - MOT expiry date

    Returns a structured risk summary suitable for a car-buying decision.

    Args:
        registration: UK vehicle registration number, e.g. "AB12CDE"
    """
    raw = get_mot_history(registration)

    if "error" in raw:
        return raw

    # The API returns a list; take the first (and only) vehicle
    vehicle = raw if isinstance(raw, dict) else raw[0] if isinstance(raw, list) else {}
    tests   = vehicle.get("motTests", [])

    if not tests:
        return {"error": "No MOT tests on record for this vehicle"}

    failures          = [t for t in tests if t.get("testResult") == "FAILED"]
    passes            = [t for t in tests if t.get("testResult") == "PASSED"]
    recent_tests      = tests[:6]  # last ~3 years (2 per year)
    recent_failures   = [t for t in recent_tests if t.get("testResult") == "FAILED"]

    # Mileage consistency
    mileage_readings = []
    for t in tests:
        try:
            mileage_readings.append((t["completedDate"], int(t["odometerValue"])))
        except (KeyError, ValueError, TypeError):
            pass
    mileage_readings.sort(key=lambda x: x[0])
    mileage_drop = any(
        mileage_readings[i][1] > mileage_readings[i + 1][1]
        for i in range(len(mileage_readings) - 1)
    )

    # Collect all RFRs (reasons for refusal / advisories)
    all_rfr = []
    for t in tests:
        for item in t.get("rfrAndComments", []):
            all_rfr.append({
                "date":     t.get("completedDate"),
                "type":     item.get("type"),       # FAIL / ADVISORY / PRS
                "text":     item.get("text"),
                "category": _categorise_rfr(item.get("text", "")),
            })

    advisory_only = [r for r in all_rfr if r["type"] == "ADVISORY"]
    fail_items    = [r for r in all_rfr if r["type"] in ("FAIL", "PRS")]

    # Category frequency
    cat_counts: dict = {}
    for r in fail_items:
        cat_counts[r["category"]] = cat_counts.get(r["category"], 0) + 1

    latest_test = tests[0]

    return {
        "vehicle": {
            "registration":    vehicle.get("registration"),
            "make":            vehicle.get("make"),
            "model":           vehicle.get("model"),
            "colour":          vehicle.get("primaryColour"),
            "fuelType":        vehicle.get("fuelType"),
            "engineSize":      vehicle.get("engineSize"),
            "firstUsedDate":   vehicle.get("firstUsedDate"),
            "manufactureYear": vehicle.get("manufactureYear"),
        },
        "summary": {
            "totalTests":          len(tests),
            "totalPasses":         len(passes),
            "totalFailures":       len(failures),
            "recentFailures3yr":   len(recent_failures),
            "mileageDiscrepancy":  mileage_drop,
            "latestResult":        latest_test.get("testResult"),
            "latestTestDate":      latest_test.get("completedDate"),
            "motExpiryDate":       latest_test.get("expiryDate"),
            "latestMileage":       latest_test.get("odometerValue"),
        },
        "failureCategories": cat_counts,
        "advisories":        advisory_only[:10],   # top 10
        "recentFailureItems": fail_items[:15],
        "riskFlags": _build_risk_flags(recent_failures, mileage_drop, advisory_only, cat_counts),
    }


def _categorise_rfr(text: str) -> str:
    """Map RFR text to a high-level category."""
    t = text.lower()
    if any(k in t for k in ["brake", "braking"]):          return "Brakes"
    if any(k in t for k in ["tyre", "tire"]):              return "Tyres"
    if any(k in t for k in ["light", "lamp", "bulb"]):     return "Lights"
    if any(k in t for k in ["emission", "exhaust", "co2"]): return "Emissions"
    if any(k in t for k in ["steering", "track rod"]):     return "Steering"
    if any(k in t for k in ["suspension", "shock", "spring", "wishbone"]): return "Suspension"
    if any(k in t for k in ["wiper", "windscreen", "screen"]): return "Windscreen/Wipers"
    if any(k in t for k in ["rust", "corrosion", "sill", "chassis"]): return "Bodywork/Rust"
    if any(k in t for k in ["seat belt", "seatbelt"]):     return "Seat Belts"
    return "Other"


def _build_risk_flags(recent_failures, mileage_drop, advisories, cat_counts) -> list:
    flags = []
    if len(recent_failures) >= 2:
        flags.append("⚠️  Multiple failures in last 3 years — mechanically unreliable history")
    if mileage_drop:
        flags.append("🚨  Mileage discrepancy detected — possible clocking")
    if cat_counts.get("Brakes", 0) >= 2:
        flags.append("⚠️  Recurring brake failures — inspect carefully")
    if cat_counts.get("Suspension", 0) >= 2:
        flags.append("⚠️  Recurring suspension issues — can be costly to fix")
    if cat_counts.get("Emissions", 0) >= 2:
        flags.append("⚠️  Recurring emissions failures — engine concern")
    if cat_counts.get("Bodywork/Rust", 0) >= 1:
        flags.append("⚠️  Rust/corrosion noted — check sills and chassis")
    if len(advisories) >= 5:
        flags.append("ℹ️  High advisory count — several items may need attention soon")
    if not flags:
        flags.append("✅  No major red flags in MOT history")
    return flags


if __name__ == "__main__":
    # Use streamable-http transport for Cloud Run, stdio for local development
    if os.getenv("PORT"):
        mcp.run(transport="streamable-http")
    else:
        # Running locally - use stdio transport
        mcp.run(transport="stdio")