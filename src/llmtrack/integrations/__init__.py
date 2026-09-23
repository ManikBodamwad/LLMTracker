"""
Integration adapters and auto-patching for LLM client SDKs.
"""

from llmtrack.integrations.anthropic import patch_anthropic
from llmtrack.integrations.litellm import patch_litellm
from llmtrack.integrations.openai import patch_openai

__all__ = ["patch_anthropic", "patch_litellm", "patch_openai"]
