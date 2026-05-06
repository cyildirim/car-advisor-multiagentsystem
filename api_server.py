"""
Car Advisor API Server
Exposes the ADK multi-agent pipeline as a FastAPI endpoint.
Run: uvicorn api_server:app --reload --port 8000
"""
import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add agents dir to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))
from agent import analyse_listing

app = FastAPI(title="Car Buying Advisor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CarListing(BaseModel):
    registration: str
    make: str
    model: str
    year: int
    mileage: int
    asking_price: float
    fuel_type: str
    engine_size: str
    description: str


@app.post("/analyse")
async def analyse(listing: CarListing):
    try:
        result = await analyse_listing(listing.model_dump())
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Agent returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
