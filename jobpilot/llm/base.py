"""
LLM and Embedding Provider interfaces for JobPilot AI.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMProvider(ABC):
    """Abstract interface for LLM completions, structured outputs, and classifications."""

    @abstractmethod
    async def complete(self, prompt: str, system: str = "", temperature: float = 0.1) -> str:
        """Generate text completion from prompt."""
        pass

    @abstractmethod
    async def structured_output(self, prompt: str, schema: Dict[str, Any], system: str = "") -> Dict[str, Any]:
        """Generate structured JSON conforming to schema."""
        pass

    @abstractmethod
    async def classify(self, text: str, categories: List[str], system: str = "") -> str:
        """Classify input text into one of the provided categories."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class EmbeddingProvider(ABC):
    """Abstract interface for text embeddings."""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Compute embedding vectors for a batch of strings."""
        pass

    @abstractmethod
    async def embed_one(self, text: str) -> List[float]:
        """Compute embedding vector for a single string."""
        pass
