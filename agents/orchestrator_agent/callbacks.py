
import logging
import time
from typing import Optional
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai import types
logger = logging.getLogger(__name__)


# Track agent start times for duration logging
_agent_execution_tracker: dict[str, float] = {}

def _extract_session_id(session) -> str:
    """Extract session ID from session object."""
    if session is None:
        return "unknown"
    return getattr(session, 'id', getattr(session, 'session_id', 'unknown'))
 

async def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    try:
        print(f"\n{'─'*50}")
        print(f"■ AGENT START: {getattr(callback_context, 'agent_name', 'unknown')}")
        print(f"{'─'*50}")
        memory_service = callback_context._invocation_context.memory_service
        session = callback_context._invocation_context.session
        agent_name = getattr(callback_context, 'agent_name', 'unknown')
        session_id = _extract_session_id(session)
        execution_key = f"{agent_name}:{session_id}"
        if execution_key in _agent_execution_tracker:
            total_execution_time = time.time() - _agent_execution_tracker.pop(execution_key)
            print(f"\n{'─'*50}")
            print(f"■ AGENT DONE: {agent_name} ({total_execution_time:.1f}s)")
            print(f"{'─'*50}")
            if total_execution_time > 20:
                logger.warning("Slow agent: %s took %.2fs", agent_name, total_execution_time)
        if memory_service and hasattr(memory_service, 'add_session_to_memory'):
            events = getattr(session, 'events', [])
            await memory_service.add_session_to_memory(session)
            print(f"  💾 Session saved to memory ({len(events)} events)")
    except Exception as e:
        logger.error("after_agent_callback error: %s", e)
    return None