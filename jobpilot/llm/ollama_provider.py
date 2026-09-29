"""
Ollama Provider for Local LLM and Embeddings.
Uses local models (llama3.1:8b, nomic-embed-text) via HTTP API.
Entirely local, private, and free.
"""

import json
import re
from typing import Any, Dict, List, Optional
import httpx

from jobpilot.llm.base import LLMProvider, EmbeddingProvider
from jobpilot.core.registry import PluginRegistry


@PluginRegistry.register_provider("ollama")
class OllamaProvider(LLMProvider, EmbeddingProvider):
    """Local LLM and embedding provider powered by Ollama."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        embedding_model: str = "nomic-embed-text",
        timeout: float = 60.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._embedding_model = embedding_model
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.1) -> str:
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": self._model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "").strip()
            except httpx.ConnectError:
                raise ConnectionError(f"Cannot connect to Ollama at {self._base_url}. Ensure 'ollama serve' is running.")

    async def structured_output(self, prompt: str, schema: Dict[str, Any], system: str = "") -> Dict[str, Any]:
        """Request JSON format from Ollama and parse result."""
        url = f"{self._base_url}/api/generate"
        json_instruction = (
            f"\n\nYou must return ONLY a valid JSON object strictly matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\nDo not include any explanation or markdown formatting."
        )
        full_prompt = prompt + json_instruction

        payload = {
            "model": self._model,
            "prompt": full_prompt,
            "system": system,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                raw_text = data.get("response", "{}")
                return json.loads(raw_text)
            except json.JSONDecodeError:
                # Fallback: extract JSON from response using regex
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                raise ValueError(f"Ollama output could not be parsed as JSON: {raw_text}")
            except httpx.ConnectError:
                raise ConnectionError(f"Cannot connect to Ollama at {self._base_url}. Ensure 'ollama serve' is running.")

    async def classify(self, text: str, categories: List[str], system: str = "") -> str:
        prompt = (
            f"Classify the following text into exactly one of these categories: {', '.join(categories)}.\n"
            f"Return only the selected category name and nothing else.\n\n"
            f"Text:\n{text}"
        )
        raw = await self.complete(prompt, system=system, temperature=0.0)
        clean = raw.strip().strip('"').strip("'")
        for cat in categories:
            if cat.lower() in clean.lower():
                return cat
        return categories[0]

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding via Ollama /api/embeddings."""
        results = []
        for t in texts:
            vec = await self.embed_one(t)
            results.append(vec)
        return results

    async def embed_one(self, text: str) -> List[float]:
        url = f"{self._base_url}/api/embeddings"
        payload = {
            "model": self._embedding_model,
            "prompt": text,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding", [])
            except httpx.ConnectError:
                raise ConnectionError(f"Cannot connect to Ollama at {self._base_url}. Ensure 'ollama serve' is running.")
