"""
Provider Factory for LLM and Embedding services.
Inspects config/settings.yaml and resolves registered providers from PluginRegistry.
"""

from typing import Optional
from jobpilot.core.feature_flags import get_settings
from jobpilot.core.registry import PluginRegistry
from jobpilot.llm.base import LLMProvider, EmbeddingProvider
# Import providers so they register with PluginRegistry
import os
from dotenv import load_dotenv
load_dotenv()

import jobpilot.llm.ollama_provider
import jobpilot.llm.nvidia_provider


def get_llm_provider(task: Optional[str] = None) -> LLMProvider:
    """Resolve LLM provider based on settings task routing or default."""
    settings = get_settings().get("llm", {})
    default_name = settings.get("default_provider", "ollama")

    # If NVIDIA key is available and user wants cloud speed or fallback
    if os.getenv("NVIDIA_API_KEY") and default_name == "nvidia":
        provider_cls = PluginRegistry.get_provider("nvidia")
        if provider_cls:
            return _instantiate_provider(provider_cls, settings, "nvidia")

    if task and "task_routing" in settings:
        task_provider = settings["task_routing"].get(task)
        if task_provider and not task_provider.endswith("_embeddings"):
            provider_cls = PluginRegistry.get_provider(task_provider)
            if provider_cls:
                return _instantiate_provider(provider_cls, settings, task_provider)

    provider_cls = PluginRegistry.get_provider(default_name)
    if not provider_cls:
        # Check if NVIDIA is available
        if os.getenv("NVIDIA_API_KEY"):
            provider_cls = PluginRegistry.get_provider("nvidia")
        else:
            provider_cls = PluginRegistry.get_provider("ollama")

    return _instantiate_provider(provider_cls, settings, default_name)


def get_embedding_provider() -> EmbeddingProvider:
    """Resolve embedding provider from settings."""
    settings = get_settings().get("llm", {})
    embed_name = settings.get("embedding_provider", "ollama")
    provider_cls = PluginRegistry.get_provider(embed_name)
    if not provider_cls:
        provider_cls = PluginRegistry.get_provider("ollama")

    return _instantiate_provider(provider_cls, settings, embed_name)


def _instantiate_provider(cls, settings: dict, name: str = "ollama"):
    if name == "nvidia" or cls.__name__ == "NvidiaProvider":
        api_key = os.getenv("NVIDIA_API_KEY", "")
        nvidia_config = settings.get("nvidia", {})
        model = nvidia_config.get("model", "nvidia/llama-3.1-nemotron-70b-instruct")
        return cls(api_key=api_key, model=model)

    ollama_config = settings.get("ollama", {})
    base_url = ollama_config.get("base_url", "http://localhost:11434")
    model = ollama_config.get("model", "llama3.1:8b")
    embedding_model = ollama_config.get("embedding_model", "nomic-embed-text")
    return cls(base_url=base_url, model=model, embedding_model=embedding_model)

