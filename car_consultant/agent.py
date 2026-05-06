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
from google.genai import types
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams


# ── Sub-agent imports ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from price_agent.price_agent import price_agent
from mot_agent.mot_agent import mot_agent


# ── Root Agent ───────────────────────────────────────────────────────────────
orchestrator_agent = Agent(
    name="car_buying_advisor",
    model=os.getenv("DEFAULT_MODEL"),
    description="Orchestrates car buying analysis across price, MOT history, and running costs agents.",
    instruction="""
You are a senior used car buying advisor for UK buyers. You coordinate three specialist agents:

Check general evaluation about car -> Check MOT History -> Check others cars from memory if there is any -> compare -> generate summary.

""",
    sub_agents=[mot_agent]
)




root_agent = orchestrator_agent