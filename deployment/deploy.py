"""
Deployment Script for Multi-Agent Customer Support System
==========================================================
This script handles:
1. Local testing of the agent
2. Deployment to Vertex AI Agent Engine
3. Testing the deployed agent

Prerequisites:
- Google Cloud Project with Vertex AI API enabled
- Authenticated via `gcloud auth application-default login`
- A GCS bucket for staging

Usage:
    python deployment/deploy.py --action [test_local|deploy|test_remote|cleanup]

"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines
from google.adk.plugins.logging_plugin import LoggingPlugin

# Load environment variables FIRST before importing agents
load_dotenv()

# Add agents directory to Python path to match runtime layout
# (both adk web and deployed environment treat agents as top-level modules)
project_root = Path(__file__).parent.parent
# agents_dir = project_root / "agents"
# sys.path.insert(0, str(agents_dir))
sys.path.insert(0, str(project_root))  # Also add project root for 'common' package

# from agents.orchestrator_agent.agent import root_agent

# =============================================================================
# CONFIGURATION - Loaded from environment variables
# =============================================================================

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
STAGING_BUCKET = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
DISPLAY_NAME = "car-advisor-multiagentsystem"

# For Express Mode (no GCP project required):
# API_KEY = "your-express-mode-api-key"


# =============================================================================
# INITIALIZATION
# =============================================================================

def init_vertex_ai():
    """Initialize Vertex AI SDK with project settings."""
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )
    print(f"✓ Initialized Vertex AI")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Staging: {STAGING_BUCKET}")


# For Express Mode initialization:
# def init_vertex_ai_express():
#     """Initialize Vertex AI in Express Mode (no GCP project needed)."""
#     vertexai.init(key=API_KEY)
#     print("✓ Initialized Vertex AI in Express Mode")



# =============================================================================
# DEPLOYMENT
# =============================================================================

def deploy_to_agent_engine():
    """Deploy the agent to Vertex AI Agent Engine with Memory Bank."""
    print("\n" + "=" * 60)
    print("DEPLOYING TO VERTEX AI AGENT ENGINE")
    print("=" * 60)
    

    init_vertex_ai()

    from agents.orchestrator_agent.agent import root_agent
    
    # Initialize Vertex AI client (needed for update call)
    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

    # Wrap agent in AdkApp with observability
    # Memory Bank will be enabled via update() after deployment
    adk_app = agent_engines.AdkApp(
        agent=root_agent,
        app_name="car_advisor",  # CRITICAL: Required for Memory Bank scope
        plugins=[LoggingPlugin()],  # Enable comprehensive observability logging
    )

    print("\n⏳ Step 1/3: Deploying agent (this may take several minutes)...")

    # Change to project root so extra_packages paths are relative in the tarball
    os.chdir(project_root)

    # Step 1: Deploy agent using module-level agent_engines.create()
    # Note: We need to know the agent_engine_id upfront for env vars, but we get it after creation
    # So we'll create first, then update with env vars
    remote_app = agent_engines.create(
        agent_engine=adk_app,
        requirements=[
            "google-cloud-aiplatform[agent_engines]>=1.132.0,<2.0.0",
            "google-adk==1.26.0",
            "requests",
            "numpy>=1.24.0",
            "vertexai>=1.38.0",
            "python-dotenv>=1.0.0",
            "google-auth",
            "google-auth-httplib2"
        ],
        extra_packages=["agents", "common"],
        display_name=DISPLAY_NAME,
        env_vars={
            "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
            "OTEL_SEMCONV_STABILITY_OPT_IN": "gen_ai_latest_experimental",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
            # Capture prompt/response as span events so they appear in the
            # Cloud Trace UI's span detail panel.
            "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS": "true",
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "MOT_MCP_STREAMABLE": os.getenv("MOT_MCP_STREAMABLE"),
            "DEFAULT_MODEL": os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
        },
    )

    # Store resource name before updates (it may change after update calls)
    resource_name = remote_app.resource_name
    agent_engine_id = resource_name.split("/")[-1]


    print("\n" + "=" * 60)
    print("✓ DEPLOYMENT SUCCESSFUL!")
    print("=" * 60)
    print(f"\nResource Name: {resource_name}")
    print(f"Agent Engine ID: {agent_engine_id}")
  

    print(f"\nUpdate your .env file with:")
    print(f'AGENT_ENGINE_RESOURCE_NAME="{resource_name}"')
    print(f"\nView in Cloud Console:")
    print(f"https://console.cloud.google.com/vertex-ai/agents/agent-engines?project={PROJECT_ID}")

    return remote_app


# =============================================================================
# TEST DEPLOYED AGENT
# =============================================================================

async def test_remote_agent(resource_name: str):
    """Test the deployed agent on Agent Engine."""
    print("\n" + "=" * 60)
    print("TESTING DEPLOYED AGENT")
    print("=" * 60)
    
    init_vertex_ai()
    
    # Connect to deployed agent
    remote_app = agent_engines.get(resource_name)
    print(f"✓ Connected to: {resource_name}")
    
    # Create remote session
    remote_session = await remote_app.async_create_session(user_id="remote_test_user")
    print(f"✓ Created remote session: {remote_session['id']}")
    
    # Test query
   
    test_query = """
    Create a complete content package for:
    - Topic: Productivity hacks using AI for remote workers
    - Target Audience: Remote professionals and digital nomads
    - Tone: Conversational and helpful
    - Keywords: AI productivity, remote work, automation tools
    """
    print(f"\n{'─' * 40}")
    print(f"USER: {test_query}")
    print(f"{'─' * 40}")
    
    async for event in remote_app.async_stream_query(
        user_id="remote_test_user",
        session_id=remote_session["id"],
        message=test_query,
    ):
        # Handle both object-style and dict-style events
        if hasattr(event, "content"):
            content = event.content
            if content and hasattr(content, "parts"):
                for part in content.parts:
                    if getattr(part, "text", None):
                        print(f"\nAGENT: {part.text}")
        elif isinstance(event, dict):
            content = event.get("content") or {}
            if isinstance(content, dict):
                for part in content.get("parts", []):
                    if isinstance(part, dict) and part.get("text"):
                        print(f"\nAGENT: {part['text']}")
    
    print("\n✓ Remote testing complete!")


# =============================================================================
# CLEANUP
# =============================================================================

def cleanup_deployment(resource_name: str):
    """Delete the deployed agent to avoid charges."""
    print("\n" + "=" * 60)
    print("CLEANING UP DEPLOYMENT")
    print("=" * 60)
    
    init_vertex_ai()
    
    remote_app = agent_engines.get(resource_name)
    remote_app.delete(force=True)  # force=True also deletes sessions
    
    print(f"✓ Deleted: {resource_name}")
    print("✓ Cleanup complete!")


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Multi-Agent Customer Support to Vertex AI Agent Engine"
    )
    parser.add_argument(
        "--action",
        choices=["deploy", "test_remote", "cleanup"],
        required=True,
        help="Action to perform"
    )
    parser.add_argument(
        "--resource_name",
        type=str,
        help="Resource name for test_remote or cleanup actions"
    )
    
    args = parser.parse_args()
    
    
    if args.action == "deploy":
        deploy_to_agent_engine()
    
    elif args.action == "test_remote":
        resource_name = args.resource_name or os.getenv("AGENT_ENGINE_RESOURCE_NAME")
        if not resource_name:
            print("ERROR: --resource_name required or set AGENT_ENGINE_RESOURCE_NAME in .env")
            return
        asyncio.run(test_remote_agent(resource_name))

    elif args.action == "cleanup":
        resource_name = args.resource_name or os.getenv("AGENT_ENGINE_RESOURCE_NAME")
        if not resource_name:
            print("ERROR: --resource_name required or set AGENT_ENGINE_RESOURCE_NAME in .env")
            return
        cleanup_deployment(resource_name)


if __name__ == "__main__":
    main()