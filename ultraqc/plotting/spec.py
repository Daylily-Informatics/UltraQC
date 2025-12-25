# -*- coding: utf-8 -*-
"""
PlotSpec - Library-agnostic plot specification data structure.

This module defines the PlotSpec class and related enums that provide
a standardized way to describe plots independent of the rendering backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    import pandas as pd


class PlotType(Enum):
    """Supported plot types."""
    BAR = auto()
    BAR_STACKED = auto()
    BAR_GROUPED = auto()
    BAR_HORIZONTAL = auto()
    LINE = auto()
    SCATTER = auto()
    SCATTER_3D = auto()
    BOX = auto()
    VIOLIN = auto()
    HISTOGRAM = auto()
    HEATMAP = auto()
    PIE = auto()
    AREA = auto()
    

class PlotMode(Enum):
    """Plot display modes."""
    MARKERS = auto()
    LINES = auto()
    LINES_MARKERS = auto()
    

class ColorScale(Enum):
    """Available color scales."""
    VIRIDIS = "viridis"
    PLASMA = "plasma"
    INFERNO = "inferno"
    MAGMA = "magma"
    CIVIDIS = "cividis"
    BLUES = "blues"
    REDS = "reds"
    GREENS = "greens"
    NEON = "neon"  # Custom UltraQC neon theme


@dataclass
class PlotStyle:
    """Styling options for plots."""
    # Colors
    color: Optional[str] = None
    colors: Optional[List[str]] = None
    color_scale: Optional[ColorScale] = None
    opacity: float = 1.0
    
    # Lines
    line_width: float = 2.0
    line_style: str = "solid"  # solid, dash, dot, dashdot
    
    # Markers
    marker_size: float = 8.0
    marker_symbol: str = "circle"
    
    # Fill
    fill: Optional[str] = None  # none, tozeroy, tozerox, tonexty, etc.
    fill_color: Optional[str] = None
    
    # Fonts
    font_family: str = "Arial, sans-serif"
    font_size: int = 12
    title_font_size: int = 16
    
    # Theme
    theme: str = "ultraqc_dark"  # ultraqc_dark, ultraqc_light, default


@dataclass
class AxisConfig:
    """Configuration for plot axes."""
    title: Optional[str] = None
    type: str = "linear"  # linear, log, category, date
    range: Optional[List[float]] = None
    tick_format: Optional[str] = None
    show_grid: bool = True
    show_line: bool = True
    zero_line: bool = False


@dataclass 
class PlotLayout:
    """Layout configuration for plots."""
    title: Optional[str] = None
    width: Optional[int] = None
    height: int = 500
    margin: Dict[str, int] = field(default_factory=lambda: {"t": 80, "b": 80, "l": 80, "r": 40})
    
    x_axis: AxisConfig = field(default_factory=AxisConfig)
    y_axis: AxisConfig = field(default_factory=AxisConfig)
    z_axis: Optional[AxisConfig] = None
    
    show_legend: bool = True
    legend_position: str = "right"  # right, left, top, bottom
    
    hover_mode: str = "closest"  # closest, x, y, x unified, y unified
    bar_mode: str = "stack"  # stack, group, overlay, relative
    
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    shapes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PlotSeries:
    """A single data series in a plot."""
    name: str
    x: Optional[List[Any]] = None
    y: Optional[List[Any]] = None
    z: Optional[List[Any]] = None
    text: Optional[List[str]] = None
    
    # Series-specific styling
    style: Optional[PlotStyle] = None
    mode: PlotMode = PlotMode.MARKERS
    visible: bool = True
    
    # For grouped/categorized data
    group: Optional[str] = None
    
    # Additional series-specific options
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlotSpec:
    """
    Library-agnostic plot specification.
    
    This class standardizes plot configuration in a way that can be
    translated to any supported rendering backend.
    """
    plot_type: PlotType

    # Data can be provided as DataFrame or as series
    data: Optional["pd.DataFrame"] = None
    series: List[PlotSeries] = field(default_factory=list)
    
    # Column mappings when using DataFrame
    x: Optional[str] = None
    y: Optional[str] = None
    z: Optional[str] = None
    color: Optional[str] = None  # Column to use for color mapping
    size: Optional[str] = None   # Column to use for size mapping
    text: Optional[str] = None   # Column to use for hover text
    group: Optional[str] = None  # Column to use for grouping
    
    # Layout and styling
    layout: PlotLayout = field(default_factory=PlotLayout)
    style: PlotStyle = field(default_factory=PlotStyle)
    
    # Histogram-specific
    nbins: int = 20
    
    # Interaction options
    interactive: bool = True
    show_mode_bar: bool = True
    mode_bar_buttons_to_remove: List[str] = field(default_factory=lambda: [
        "sendDataToCloud",
        "resetScale2d", 
        "hoverClosestCartesian",
        "hoverCompareCartesian",
        "toggleSpikelines",
    ])
    
    # Metadata
    plot_id: Optional[str] = None
    source: str = "ultraqc"  # Source identifier
    
    def add_series(self, series: PlotSeries) -> "PlotSpec":
        """Add a data series to the plot."""
        self.series.append(series)
        return self
    
    def with_layout(self, **kwargs) -> "PlotSpec":
        """Update layout with given kwargs."""
        for key, value in kwargs.items():
            if hasattr(self.layout, key):
                setattr(self.layout, key, value)
        return self
    
    def with_style(self, **kwargs) -> "PlotSpec":
        """Update style with given kwargs."""
        for key, value in kwargs.items():
            if hasattr(self.style, key):
                setattr(self.style, key, value)
        return self

