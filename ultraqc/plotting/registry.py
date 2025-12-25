# -*- coding: utf-8 -*-
"""
RendererRegistry - Plugin registry for visualization backends.

This module provides a centralized registry for managing plot renderer
plugins, allowing runtime selection and fallback handling.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Type

from ultraqc.plotting.base import PlotRenderer, RenderError
from ultraqc.plotting.spec import PlotType

logger = logging.getLogger(__name__)


class RendererRegistry:
    """
    Central registry for plot renderer plugins.
    
    This class manages the registration, discovery, and selection of
    rendering backends. It supports:
    - Registration of new renderers
    - Default renderer selection via configuration
    - Per-plot-type renderer selection
    - Graceful fallback when renderers fail
    
    Usage:
        # Register a renderer
        registry = RendererRegistry()
        registry.register(PlotlyRenderer)
        
        # Get the default renderer
        renderer = registry.get_renderer()
        
        # Get a specific renderer
        renderer = registry.get_renderer("ggplot")
    """
    
    _instance: Optional["RendererRegistry"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "RendererRegistry":
        """Singleton pattern to ensure one global registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the registry (only once due to singleton)."""
        if self._initialized:
            return
            
        self._renderers: Dict[str, Type[PlotRenderer]] = {}
        self._instances: Dict[str, PlotRenderer] = {}
        self._default_renderer: str = "plotly"
        self._plot_type_renderers: Dict[PlotType, str] = {}
        self._fallback_renderer: str = "plotly"
        
        RendererRegistry._initialized = True
        
        # Auto-discover and register built-in renderers
        self._auto_register_builtins()
    
    def _auto_register_builtins(self) -> None:
        """Automatically register built-in renderers."""
        try:
            from ultraqc.plotting.renderers.plotly_renderer import PlotlyRenderer
            self.register(PlotlyRenderer)
        except ImportError as e:
            logger.warning(f"Could not load PlotlyRenderer: {e}")
        
        try:
            from ultraqc.plotting.renderers.ggplot_renderer import GGPlotRenderer
            self.register(GGPlotRenderer)
        except ImportError as e:
            logger.debug(f"GGPlotRenderer not available: {e}")
        
        try:
            from ultraqc.plotting.renderers.echarts_renderer import EChartsRenderer
            self.register(EChartsRenderer)
        except ImportError as e:
            logger.debug(f"EChartsRenderer not available: {e}")
    
    def register(self, renderer_class: Type[PlotRenderer]) -> None:
        """
        Register a renderer class.
        
        Args:
            renderer_class: The renderer class to register
        """
        name = renderer_class.name
        if name in self._renderers:
            logger.warning(f"Overwriting existing renderer: {name}")
        self._renderers[name] = renderer_class
        logger.debug(f"Registered renderer: {name}")
    
    def unregister(self, name: str) -> None:
        """
        Unregister a renderer.
        
        Args:
            name: Name of the renderer to unregister
        """
        if name in self._renderers:
            del self._renderers[name]
            if name in self._instances:
                del self._instances[name]
            logger.debug(f"Unregistered renderer: {name}")
    
    def get_renderer(
        self, 
        name: Optional[str] = None,
        plot_type: Optional[PlotType] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> PlotRenderer:
        """
        Get a renderer instance.
        
        Args:
            name: Specific renderer name (overrides default)
            plot_type: Get renderer configured for this plot type
            config: Optional configuration for the renderer
            
        Returns:
            PlotRenderer instance
            
        Raises:
            ValueError: If no suitable renderer is found
        """
        # Determine which renderer to use
        renderer_name = name
        if renderer_name is None and plot_type is not None:
            renderer_name = self._plot_type_renderers.get(plot_type)
        if renderer_name is None:
            renderer_name = self._get_configured_default()
        if renderer_name is None:
            renderer_name = self._default_renderer
        
        # Try to get the renderer, with fallback
        try:
            return self._get_or_create_instance(renderer_name, config)
        except Exception as e:
            logger.error(f"Failed to get renderer '{renderer_name}': {e}")
            if renderer_name != self._fallback_renderer:
                logger.info(f"Falling back to {self._fallback_renderer}")
                return self._get_or_create_instance(self._fallback_renderer, config)
            raise ValueError(f"No renderer available: {e}")
    
    def _get_configured_default(self) -> Optional[str]:
        """Get the default renderer from environment/settings."""
        # Check environment variable first
        env_renderer = os.environ.get("ULTRAQC_PLOT_RENDERER")
        if env_renderer and env_renderer.lower() in self._renderers:
            return env_renderer.lower()

        # Try to get from settings
        try:
            from ultraqc.settings import get_settings
            settings = get_settings()
            if hasattr(settings, "PLOT_RENDERER"):
                return getattr(settings, "PLOT_RENDERER")
        except Exception:
            pass

        return None

    def _get_or_create_instance(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> PlotRenderer:
        """Get or create a renderer instance."""
        if name not in self._renderers:
            raise ValueError(f"Unknown renderer: {name}")

        # Create new instance if config provided or not cached
        if config is not None or name not in self._instances:
            renderer_class = self._renderers[name]
            instance = renderer_class(config)
            if config is None:
                self._instances[name] = instance
            return instance

        return self._instances[name]

    def set_default(self, name: str) -> None:
        """
        Set the default renderer.

        Args:
            name: Name of the renderer to use as default
        """
        if name not in self._renderers:
            raise ValueError(f"Unknown renderer: {name}")
        self._default_renderer = name

    def set_renderer_for_plot_type(self, plot_type: PlotType, renderer: str) -> None:
        """
        Set a specific renderer for a plot type.

        Args:
            plot_type: The plot type
            renderer: Name of the renderer to use
        """
        if renderer not in self._renderers:
            raise ValueError(f"Unknown renderer: {renderer}")
        self._plot_type_renderers[plot_type] = renderer

    def list_renderers(self) -> List[Dict[str, Any]]:
        """
        List all registered renderers.

        Returns:
            List of renderer info dictionaries
        """
        result = []
        for name, renderer_class in self._renderers.items():
            try:
                instance = self._get_or_create_instance(name)
                result.append(instance.get_info())
            except Exception as e:
                result.append({
                    "name": name,
                    "error": str(e),
                    "available": False,
                })
        return result

    def is_available(self, name: str) -> bool:
        """
        Check if a renderer is available.

        Args:
            name: Name of the renderer

        Returns:
            True if the renderer is registered and functional
        """
        if name not in self._renderers:
            return False
        try:
            self._get_or_create_instance(name)
            return True
        except Exception:
            return False

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None
        cls._initialized = False


# Module-level convenience functions
_registry: Optional[RendererRegistry] = None


def _get_registry() -> RendererRegistry:
    """Get or create the global registry instance."""
    global _registry
    if _registry is None:
        _registry = RendererRegistry()
    return _registry


def get_renderer(
    name: Optional[str] = None,
    plot_type: Optional[PlotType] = None,
    config: Optional[Dict[str, Any]] = None
) -> PlotRenderer:
    """
    Get a renderer instance from the global registry.

    Args:
        name: Specific renderer name
        plot_type: Get renderer configured for this plot type
        config: Optional configuration

    Returns:
        PlotRenderer instance
    """
    return _get_registry().get_renderer(name, plot_type, config)


def get_renderer_by_name(name: str) -> PlotRenderer:
    """
    Get a specific renderer by name.

    Args:
        name: The renderer name

    Returns:
        PlotRenderer instance
    """
    return _get_registry().get_renderer(name=name)


def register_renderer(renderer_class: Type[PlotRenderer]) -> None:
    """
    Register a renderer class with the global registry.

    Args:
        renderer_class: The renderer class to register
    """
    _get_registry().register(renderer_class)


def list_renderers() -> List[Dict[str, Any]]:
    """
    List all registered renderers.

    Returns:
        List of renderer info dictionaries
    """
    return _get_registry().list_renderers()

