# 🚗 Car Buying Advisor — ADK + A2A + MOT MCP

A multi-agent car buying analysis system built with Google ADK and the Agent2Agent (A2A) protocol.
Paste any UK used car listing and get a **Buy / Negotiate / Walk Away** verdict in seconds.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Car Buying Advisor UI              │
│         (React — claude.ai Artifact)            │
└───────────────────┬─────────────────────────────┘
                    │ POST /analyse
┌───────────────────▼─────────────────────────────┐
│           FastAPI API Server                    │
│              api_server.py                      │
└───────────────────┬─────────────────────────────┘
                    │ ADK Runner
┌───────────────────▼─────────────────────────────┐
│         Root Orchestrator Agent                 │
│         (car_buying_advisor)                    │
│                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────┐ │
│  │ price_agent  │ │  mot_agent   │ │ running │ │
│  │              │ │              │ │ _costs  │ │
│  │ Is the price │ │ MOT history  │ │ agent   │ │
│  │ fair?        │ │ + listing    │ │         │ │
│  │              │ │ red flags    │ │ Annual  │ │
│  │              │ │              │ │ costs   │ │
│  └──────────────┘ └──────┬───────┘ └─────────┘ │
└─────────────────────────┬┼────────────────────── ┘
                          ││ MCP (stdio)
              ┌───────────▼▼──────────┐
              │   MOT MCP Server      │
              │  mot_mcp_server.py    │
              │                       │
              │  DVSA MOT History API │
              │  (new v1 REST API)    │
              └───────────────────────┘
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
# Google Gemini (for ADK agents)
export GOOGLE_API_KEY=your_gemini_api_key

# DVSA MOT History API (register at https://documentation.history.mot.api.gov.uk)
export MOT_API_KEY=your_mot_api_key
export MOT_CLIENT_ID=your_azure_client_id
export MOT_CLIENT_SECRET=your_azure_client_secret
export MOT_TENANT_ID=your_azure_tenant_id
```

### 3. Register for the MOT API
Go to: https://documentation.history.mot.api.gov.uk/mot-history-api/register
- Free for individuals
- You'll receive Azure AD credentials + API key by email (usually within 2 working days)

### 4. Configure ADK to use the MOT MCP Server

Create `~/.adk/mcp_config.json`:
```json
{
  "mcpServers": {
    "mot-history": {
      "command": "python",
      "args": ["/path/to/car-advisor/mcp_server/mot_mcp_server.py"],
      "env": {
        "MOT_API_KEY": "${MOT_API_KEY}",
        "MOT_CLIENT_ID": "${MOT_CLIENT_ID}",
        "MOT_CLIENT_SECRET": "${MOT_CLIENT_SECRET}",
        "MOT_TENANT_ID": "${MOT_TENANT_ID}"
      }
    }
  }
}
```

### 5. Run the API server
```bash
uvicorn api_server:app --reload --port 8000
```

### 6. Test directly with the CLI
```bash
cd agents
python root_agent.py
```

---

## A2A: Exposing agents as remote services

To expose any agent as a standalone A2A service (e.g. the price agent as a microservice):

```python
# In price_agent.py, add:
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import uvicorn

if __name__ == "__main__":
    a2a_app = to_a2a(price_agent, port=8001)
    uvicorn.run(a2a_app, host="0.0.0.0", port=8001)
```

Then consume it from the root agent:
```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

remote_price_agent = RemoteA2aAgent(
    name="price_fairness_agent",
    description="Remote price fairness checker",
    agent_card=f"http://localhost:8001/{AGENT_CARD_WELL_KNOWN_PATH}",
)
```

---

## Project Structure

```
car-advisor/
├── requirements.txt
├── api_server.py          # FastAPI bridge
├── agents/
│   ├── root_agent.py      # Orchestrator + CLI entry point
│   ├── price_agent.py     # Price fairness sub-agent
│   ├── mot_agent.py       # MOT risk sub-agent
│   └── running_costs_agent.py  # Running costs sub-agent
└── mcp_server/
    └── mot_mcp_server.py  # DVSA MOT API wrapped as MCP
```

# Setup

Proxy mcp server as start like following

```
gcloud run services proxy mcp-server --region=us-central1
```

## web run

```
uv run adk web agents --port 8080 \
    --extra_plugins google.adk.plugins.logging_plugin.LoggingPlugin
```

## Test prompt

```
I am considering following listing for a family car. please analyse with reg: FN09XUY 2009 Toyota Avensis 1.8 V-Matic TR Tourer Euro 4 5dr £3,000 Mileage:131,140 miles 2009 (09 reg) Fuel type:Petrol Body type:Estate Engine:1.8L Gearbox:Manual Seats: 5 Emission class:Euro 4
```