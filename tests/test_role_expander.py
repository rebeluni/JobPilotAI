"""
Tests for RoleExpander (Phase 2).
"""

import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock
from jobpilot.discovery.role_expander import RoleExpander
from jobpilot.core.schemas import RoleExpansion


@pytest.mark.asyncio
async def test_role_expander_with_mock_llm():
    """Verify RoleExpander invokes LLM and parses three tiers correctly."""
    mock_llm = MagicMock()
    mock_llm.structured_output = AsyncMock(return_value={
        "exact_titles": ["AI Engineer", "Generative AI Developer"],
        "adjacent_titles": ["AI Automation Engineer", "Applied AI Specialist"],
        "stretch_titles": ["AI Solutions Architect"],
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, "test_cache.yaml")
        expander = RoleExpander(llm_provider=mock_llm, cache_path=cache_file)

        expansion = await expander.expand(["AI_ENGINEER"])
        assert len(expansion.exact_titles) == 2
        assert len(expansion.adjacent_titles) == 2
        assert len(expansion.stretch_titles) == 1
        assert expansion.approved is False
        assert expansion.pending_review is True

        # Approve expansion
        approved = expander.approve_expansion()
        assert approved.approved is True
        assert approved.pending_review is False

        # Load cached version without invoking LLM again
        cached = expander.load_cache()
        assert cached is not None
        assert cached.approved is True


@pytest.mark.asyncio
async def test_role_expander_fallback():
    """Verify deterministic fallback when LLM fails or is offline."""
    mock_failing_llm = MagicMock()
    mock_failing_llm.structured_output = AsyncMock(side_effect=ConnectionError("Ollama offline"))

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, "test_cache_fallback.yaml")
        expander = RoleExpander(llm_provider=mock_failing_llm, cache_path=cache_file)

        expansion = await expander.expand(["AI_AUTOMATION", "AI_ENGINEER"])
        assert len(expansion.exact_titles) > 0
        assert len(expansion.adjacent_titles) > 0
        assert expansion.pending_review is True
