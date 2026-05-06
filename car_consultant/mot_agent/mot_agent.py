"""
MOT & Listing Risk Agent
Combines MOT history data with the car listing description to surface issues.
"""
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
import os

# This agent consumes the MOT MCP server via the A2A-wrapped tool agent
# In local dev the MCP is accessed as a tool; in production it runs as a RemoteA2aAgent
mot_agent = Agent(
    name="mot_risk_agent",
    model=os.getenv("DEFAULT_MODEL"),
    description="Analyses MOT history data and the seller's listing description to surface potential mechanical and safety risks.",
    instruction="""
You are a vehicle inspection expert and used car risk analyst for the UK market.

You will receive:
1. The MOT history (from the MOT History API) use get_mot_history gets registration as parameter from mcp tool set to find that
2. The seller's listing description text

Your job is to:
- Cross-reference the listing claims with the MOT history
  (e.g. seller says "full service history" but lots of advisories — flag it)
- Highlight recurring failure categories
- Flag any mileage discrepancies
- Note any red flags in the listing language
  (e.g. "selling due to upgrade", "new clutch", "just passed MOT" — common deflections)
- Surface the top 3 concerns in plain English
- Return brand, model and year information to main agent


""",
  tools=[
      McpToolset(
          connection_params=StreamableHTTPConnectionParams(url='http://127.0.0.1:8080/mcp')
      )
  ],
  output_key='mot_analysis'
)
