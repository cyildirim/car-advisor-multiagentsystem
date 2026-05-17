"""
Common retry and generation configuration for Google GenAI API calls.
"""
from google.genai import types

# Configure retry behavior and generation parameters
GENERATE_CONTENT_CONFIG = types.GenerateContentConfig(
    temperature=0.7,
    top_p=0.95,
    top_k=40,
    max_output_tokens=8192,
)
