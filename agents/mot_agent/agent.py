"""
MOT & Listing Risk Agent
Combines MOT history data with the car listing description to surface issues.
"""
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest
import os
import time
from dotenv import load_dotenv
import requests as http_requests
import google.auth
import google.oauth2.id_token

# Load environment variables
load_dotenv()
mcp_server_url = os.getenv("MOT_MCP_STREAMABLE")

def get_id_token():
    """Get an ID token to authenticate with the MCP server."""
    target_url = os.getenv("MOT_MCP_STREAMABLE")
    audience = target_url.split('/mcp/')[0]
    request = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(request, audience)
    return id_token

# This agent consumes the MOT MCP server via explicitly defined tool wrappers
mot_agent = Agent(
    name="mot_risk_agent",
    model=os.getenv("DEFAULT_MODEL"),
    description="Analyses MOT history data and the seller's listing description to surface potential mechanical and safety risks.",
    instruction="""
You are a vehicle inspection expert and used car risk analyst for the UK market.

When you receive a car registration number:
1. ALWAYS call get_mot_history(registration) tool with the registration plate
2. Wait for the tool response before proceeding
3. Analyze the MOT history data returned by the tool

Available tools:
- get_mot_history: Gets full MOT test history with all details. Takes a registration plate as input.

## Your Analysis Should Include:

After receiving MOT data from your tool:
- Vehicle details (make, model, year, engine size, fuel type)
- MOT test history (passes, failures, most recent test date)
- Risk assessment (failure patterns, advisories, mileage consistency)

## Output Format:

Provide a structured summary with:
- Vehicle Information (make, model, year from MOT data)
- MOT Status (latest test result, expiry date, current mileage)
- Risk Level (LOW/MEDIUM/HIGH based on failure history)
- Top 3 Concerns (in plain English)
- Recommendation (any specific checks to do during viewing)
""",
  tools=[
      McpToolset(
          connection_params=StreamableHTTPConnectionParams(
              url=mcp_server_url,
              headers={
                    "Authorization": f"Bearer {get_id_token()}"
                }
          ),
          errlog=None,  # You can provide a logger here
      )
  ],
  output_key='mot_analysis'
)

root_agent = mot_agent