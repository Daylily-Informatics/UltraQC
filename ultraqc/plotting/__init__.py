# -*- coding: utf-8 -*-
"""
UltraQC Plotting Module - Pluggable Visualization Backend System.

This module provides a flexible plugin architecture for plot rendering,
allowing users to choose between different visualization backends while
maintaining backward compatibility with existing functionality.

Available backends:
- plotly: Default interactive charts using Plotly.js
- ggplot: Grammar of graphics style using plotnine
- echarts: High-performance charts using Apache ECharts

Usage:
    from ultraqc.plotting import get_renderer, PlotSpec, PlotType

    # Create a plot specification
    spec = PlotSpec(
        plot_type=PlotType.SCATTER,
        data=my_dataframe,
        x="x_column",
        y="y_column",
        title="My Plot"
    )

    # Get the configured renderer and render
    renderer = get_renderer()
    html = renderer.render(spec)
"""

from ultraqc.plotting.spec import PlotSpec, PlotType, PlotStyle
from ultraqc.plotting.registry import (
    RendererRegistry,
    get_renderer,
    get_renderer_by_name,
    register_renderer,
    list_renderers,
)
from ultraqc.plotting.base import PlotRenderer

__all__ = [
    # Core classes
    "PlotSpec",
    "PlotType",
    "PlotStyle",
    "PlotRenderer",
    # Registry functions
    "RendererRegistry",
    "get_renderer",
    "get_renderer_by_name",
    "register_renderer",
    "list_renderers",
]

