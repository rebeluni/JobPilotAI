"""
Central Plugin Registry for JobPilot AI.
Enables pluggable discovery sources, LLM providers, document renderers, and ATS handlers.
"""

from typing import Any, Callable, Dict, List, Optional, Type


class PluginRegistry:
    """
    Central registry for swappable components.
    Adding a new discovery source, LLM provider, document renderer, or ATS handler
    only requires registering the class using the appropriate decorator.
    """
    _discovery_sources: Dict[str, Type[Any]] = {}
    _llm_providers: Dict[str, Type[Any]] = {}
    _document_renderers: Dict[str, Type[Any]] = {}
    _ats_handlers: Dict[str, Type[Any]] = {}

    @classmethod
    def register_source(cls, name: str) -> Callable[[Type[Any]], Type[Any]]:
        """Decorator to register a discovery source plugin."""
        def decorator(klass: Type[Any]) -> Type[Any]:
            cls._discovery_sources[name.lower()] = klass
            return klass
        return decorator

    @classmethod
    def register_provider(cls, name: str) -> Callable[[Type[Any]], Type[Any]]:
        """Decorator to register an LLM or embedding provider plugin."""
        def decorator(klass: Type[Any]) -> Type[Any]:
            cls._llm_providers[name.lower()] = klass
            return klass
        return decorator

    @classmethod
    def register_renderer(cls, format_name: str) -> Callable[[Type[Any]], Type[Any]]:
        """Decorator to register a document renderer (e.g. pdf, docx, txt)."""
        def decorator(klass: Type[Any]) -> Type[Any]:
            cls._document_renderers[format_name.lower()] = klass
            return klass
        return decorator

    @classmethod
    def register_ats(cls, ats_name: str) -> Callable[[Type[Any]], Type[Any]]:
        """Decorator to register an ATS handler (e.g. greenhouse, lever, workday)."""
        def decorator(klass: Type[Any]) -> Type[Any]:
            cls._ats_handlers[ats_name.lower()] = klass
            return klass
        return decorator

    @classmethod
    def get_source(cls, name: str) -> Optional[Type[Any]]:
        return cls._discovery_sources.get(name.lower())

    @classmethod
    def get_provider(cls, name: str) -> Optional[Type[Any]]:
        return cls._llm_providers.get(name.lower())

    @classmethod
    def get_renderer(cls, format_name: str) -> Optional[Type[Any]]:
        return cls._document_renderers.get(format_name.lower())

    @classmethod
    def get_ats(cls, ats_name: str) -> Optional[Type[Any]]:
        return cls._ats_handlers.get(ats_name.lower())

    @classmethod
    def list_sources(cls) -> List[str]:
        return list(cls._discovery_sources.keys())

    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls._llm_providers.keys())

    @classmethod
    def list_renderers(cls) -> List[str]:
        return list(cls._document_renderers.keys())

    @classmethod
    def list_ats(cls) -> List[str]:
        return list(cls._ats_handlers.keys())
