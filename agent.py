"""
Car Buying Advisor — Root Orchestrator Agent
Coordinates three specialist sub-agents and returns a unified Buy/Negotiate/Walk Away verdict.
"""
import asyncio
import json
import os
import sys
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

# ── Sub-agent imports ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from price_agent import price_agent
from mot_agent import mot_agent
from car_consultant.running_costs_agent import running_costs_agent


# ── Root Agent ───────────────────────────────────────────────────────────────
root_agent = Agent(
    name="car_buying_advisor",
    model="gemini-2.5-flash-lite",
    description="Orchestrates car buying analysis across price, MOT history, and running costs agents.",
    instruction="""
You are a senior used car buying advisor for UK buyers. You coordinate three specialist agents:
- price_fairness_agent: evaluates whether the asking price is fair
- mot_risk_agent: analyses MOT history and listing red flags
- running_costs_agent: estimates annual running costs

When given a car listing (with registration number, make, model, year, mileage, price, and description),
you MUST call all three sub-agents and synthesise their outputs into a final recommendation.

Your final output MUST be a JSON object in this exact structure:
{
  "recommendation": "BUY" | "NEGOTIATE" | "WALK_AWAY",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "summary": "<2-3 sentence plain English summary of the car>",
  "headline_reasons": ["<reason 1>", "<reason 2>", "<reason 3>"],
  "price_analysis": { ... price agent output ... },
  "mot_analysis": { ... mot agent output ... },
  "running_costs": { ... running costs agent output ... },
  "negotiation_advice": "<if NEGOTIATE: specific tactics and target price>",
  "walk_away_reason": "<if WALK_AWAY: the single clearest reason>",
  "questions_to_ask_seller": ["...", "...", "..."],
  "things_to_inspect": ["...", "...", "..."]
}

Decision logic:
- BUY: price fair or under, MOT risk LOW, no major red flags
- NEGOTIATE: price slightly high OR MOT risk MEDIUM, but car is fundamentally sound
- WALK_AWAY: mileage clocking suspected, HIGH MOT risk, or severely overpriced

Only return valid JSON, no preamble or markdown fences.
""",
    sub_agents=[],
)


# ── Runner helper ─────────────────────────────────────────────────────────────
async def analyse_listing(listing: dict) -> dict:
    """
    Run the full car buying analysis pipeline.

    Args:
        listing: {
            "registration": "AB12CDE",
            "make": "Ford",
            "model": "Focus",
            "year": 2018,
            "mileage": 45000,
            "asking_price": 9500,
            "fuel_type": "Petrol",
            "engine_size": "1.0",
            "description": "Full service history, one owner, new tyres..."
        }
    Returns:
        Full analysis dict
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="car_advisor",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="car_advisor", user_id="user"
    )

    prompt = f"""
Please analyse this car listing and provide a full buying recommendation.

LISTING DETAILS:
{json.dumps(listing, indent=2)}

Call all three specialist agents (price_fairness_agent, mot_risk_agent, running_costs_agent)
and return the unified JSON verdict.
"""

    content = Content(role="user", parts=[Part(text=prompt)])
    result_text = ""

    async for event in runner.run_async(
        user_id="user",
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            result_text = event.content.parts[0].text
            break

    # Strip any markdown fences if the model added them
    result_text = result_text.strip()
    if result_text.startswith("```"):
        result_text = result_text.split("```")[1]
        if result_text.startswith("json"):
            result_text = result_text[4:]

    return json.loads(result_text)


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_listing = {
        "registration": "LD18YRM",
        "make": "Volkswagen",
        "model": "Golf",
        "year": 2018,
        "mileage": 62000,
        "asking_price": 11500,
        "fuel_type": "Petrol",
        "engine_size": "1.4",
        "description": (
            "One previous owner, full VW service history, just had new brakes fitted. "
            "Selling due to upgrade to electric. MOT until March 2026. "
            "Minor scuff on rear bumper. Drives perfectly."
        ),
    }

    result = asyncio.run(analyse_listing(sample_listing))
    print(json.dumps(result, indent=2))
