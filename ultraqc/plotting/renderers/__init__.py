# -*- coding: utf-8 -*-
"""
UltraQC Plot Renderers Package.

This package contains the built-in renderer implementations.
"""

from ultraqc.plotting.renderers.plotly_renderer import PlotlyRenderer

# Optional renderers - only import if dependencies are available
try:
    from ultraqc.plotting.renderers.ggplot_renderer import GGPlotRenderer
except ImportError:
    GGPlotRenderer = None

try:
    from ultraqc.plotting.renderers.echarts_renderer import EChartsRenderer
except ImportError:
    EChartsRenderer = None

__all__ = ["PlotlyRenderer", "GGPlotRenderer", "EChartsRenderer"]

