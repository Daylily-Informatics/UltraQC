# -*- coding: utf-8 -*-
"""
PlotRenderer - Abstract base class for visualization backends.

All rendering backends must inherit from this class and implement
the abstract methods to provide a consistent interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from ultraqc.plotting.spec import PlotSpec, PlotType

logger = logging.getLogger(__name__)


class PlotRenderer(ABC):
    """
    Abstract base class for plot rendering backends.
    
    Each backend implementation must:
    1. Implement the render() method to convert PlotSpec to output
    2. Implement supported_plot_types property
    3. Register itself with the RendererRegistry
    
    Example:
        class MyRenderer(PlotRenderer):
            name = "my_renderer"
            
            @property
            def supported_plot_types(self) -> List[PlotType]:
                return [PlotType.BAR, PlotType.LINE, PlotType.SCATTER]
            
            def render(self, spec: PlotSpec) -> str:
                # Convert spec to output format
                return "<div>My plot</div>"
    """
    
    # Renderer name - should be unique and lowercase
    name: str = "base"
    
    # Human-readable description
    description: str = "Base plot renderer"
    
    # Version string
    version: str = "1.0.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the renderer with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._validate_dependencies()
    
    def _validate_dependencies(self) -> None:
        """
        Validate that required dependencies are available.
        
        Override in subclasses to check for specific libraries.
        Raises ImportError if dependencies are missing.
        """
        pass
    
    @property
    @abstractmethod
    def supported_plot_types(self) -> List[PlotType]:
        """
        Return list of plot types supported by this renderer.
        
        Returns:
            List of PlotType enums
        """
        pass
    
    def supports(self, plot_type: PlotType) -> bool:
        """
        Check if this renderer supports a given plot type.
        
        Args:
            plot_type: The plot type to check
            
        Returns:
            True if supported, False otherwise
        """
        return plot_type in self.supported_plot_types
    
    @abstractmethod
    def render(self, spec: PlotSpec) -> str:
        """
        Render a plot specification to output format.
        
        Args:
            spec: The PlotSpec describing the plot
            
        Returns:
            HTML string containing the rendered plot
            
        Raises:
            ValueError: If plot type is not supported
            RenderError: If rendering fails
        """
        pass
    
    def render_to_file(self, spec: PlotSpec, filepath: str) -> str:
        """
        Render a plot and save to a file.
        
        Args:
            spec: The PlotSpec describing the plot
            filepath: Path to save the output
            
        Returns:
            The filepath where the plot was saved
        """
        html = self.render(spec)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        return filepath
    
    def render_to_image(self, spec: PlotSpec, format: str = "png") -> bytes:
        """
        Render a plot to a static image.
        
        Args:
            spec: The PlotSpec describing the plot
            format: Image format (png, svg, pdf, etc.)
            
        Returns:
            Image data as bytes
            
        Raises:
            NotImplementedError: If renderer doesn't support static images
        """
        raise NotImplementedError(
            f"{self.name} renderer does not support static image export"
        )
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this renderer.
        
        Returns:
            Dictionary with renderer info
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "supported_plot_types": [pt.name for pt in self.supported_plot_types],
            "config": self.config,
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"


class RenderError(Exception):
    """Exception raised when rendering fails."""
    
    def __init__(self, message: str, renderer: Optional[str] = None, 
                 spec: Optional[PlotSpec] = None):
        self.renderer = renderer
        self.spec = spec
        super().__init__(message)

