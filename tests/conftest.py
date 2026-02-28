"""Shared test configuration."""

import os

# Disable LLM API calls during testing to avoid slow retries and external dependencies.
# Tests use rule-based parsing which exercises the same routing logic.
os.environ.setdefault("GEMINI_API_KEY", "")
