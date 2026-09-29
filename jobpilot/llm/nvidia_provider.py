"""
NVIDIA NIM Cloud Provider for LLM and Embeddings.
Connects to NVIDIA API Catalog (https://integrate.api.nvidia.com/v1) using standard OpenAI-compatible API.
Supports state-of-the-art models like nvidia/llama-3.1-nemotron-70b-instruct, meta/llama-3.1-70b-instruct, etc.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from jobpilot.llm.base import LLMProvider, EmbeddingProvider
from jobpilot.core.registry import PluginRegistry

from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=True)

logger = logging.getLogger(__name__)

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"


@PluginRegistry.register_provider("nvidia")
class NvidiaProvider(LLMProvider, EmbeddingProvider):
    """NVIDIA NIM Cloud provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_NVIDIA_MODEL,
        embedding_model: str = "nvidia/nv-embed-v1",
        base_url: str = NVIDIA_BASE_URL,
        timeout: float = 60.0,
    ):
        load_dotenv(ENV_PATH, override=True)
        self._api_key = api_key or os.environ.get("NVIDIA_API_KEY", "")
        self._model = model
        self._embedding_model = embedding_model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "nvidia"

    @property
    def model_name(self) -> str:
        return self._model

    def _headers(self) -> Dict[str, str]:
        if not self._api_key:
            raise ValueError("NVIDIA_API_KEY not found. Please set NVIDIA_API_KEY in .env or settings.")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        url = f"{self._base_url}/chat/completions"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2048,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    async def structured_output(self, prompt: str, schema: Dict[str, Any], system: str = "") -> Dict[str, Any]:
        sys = (system + "\n" if system else "") + f"You MUST respond ONLY with a valid JSON object conforming to this schema:\n{json.dumps(schema, indent=2)}\nDo not include markdown code block wrappers or explanations."
        response_text = await self.complete(prompt, system=sys, temperature=0.1)

        # Clean potential markdown fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", response_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"Could not parse structured JSON from NVIDIA NIM output:\n{response_text}")

    async def classify(self, text: str, categories: List[str], system: str = "") -> str:
        cat_str = ", ".join(f'"{c}"' for c in categories)
        prompt = f"Categorize the following text into exactly ONE of these categories: [{cat_str}].\nRespond with only the category name.\n\nText:\n{text}"
        result = await self.complete(prompt, system=system, temperature=0.0)
        clean = result.strip().strip('"').strip("'")
        for c in categories:
            if c.lower() == clean.lower():
                return c
        return categories[0]

    async def embed(self, texts: List[str]) -> List[List[float]]:
        # For embeddings, if using NVIDIA NV-Embed or fallback
        url = f"{self._base_url}/embeddings"
        payload = {
            "model": self._embedding_model,
            "input": texts,
            "input_type": "passage",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, headers=self._headers(), json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return [item["embedding"] for item in data["data"]]
        except Exception as e:
            logger.warning(f"NVIDIA embedding failed, falling back: {e}")
        
        # Fallback to local or dummy if needed
        return [[0.0] * 768 for _ in texts]

    async def embed_one(self, text: str) -> List[float]:
        results = await self.embed([text])
        return results[0]
