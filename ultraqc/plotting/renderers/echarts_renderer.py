# -*- coding: utf-8 -*-
"""
EChartsRenderer - High-performance visualization backend using Apache ECharts.

This renderer provides high-performance interactive charts using the
Apache ECharts library, which is particularly good for large datasets
and complex visualizations.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from ultraqc.plotting.base import PlotRenderer, RenderError
from ultraqc.plotting.spec import (
    PlotSpec, PlotType, PlotSeries, PlotMode, PlotLayout, PlotStyle
)

logger = logging.getLogger(__name__)


# UltraQC neon theme colors
ULTRAQC_NEON_COLORS = [
    "#00ffff",  # Cyan
    "#ff00ff",  # Magenta
    "#00ff00",  # Lime
    "#ff6600",  # Orange
    "#9933ff",  # Purple
    "#ff3366",  # Pink
    "#33ccff",  # Sky blue
    "#ffff00",  # Yellow
    "#00ff99",  # Mint
    "#ff99cc",  # Rose
]


class EChartsRenderer(PlotRenderer):
    """
    Apache ECharts rendering backend.
    
    This renderer provides high-performance interactive charts that
    can handle large datasets efficiently. It uses the pyecharts
    library for Python integration.
    """
    
    name = "echarts"
    description = "High-performance charts using Apache ECharts"
    version = "1.0.0"
    
    # ECharts CDN URL
    ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        super().__init__(config)
        self._use_pyecharts = False
    
    def _validate_dependencies(self) -> None:
        """Check for pyecharts (optional, can use pure JS)."""
        try:
            import pyecharts
            self._use_pyecharts = True
        except ImportError:
            # pyecharts is optional - we can generate ECharts config directly
            self._use_pyecharts = False
            logger.debug("pyecharts not available, using direct JS generation")
    
    @property
    def supported_plot_types(self) -> List[PlotType]:
        """Plot types supported by ECharts."""
        return [
            PlotType.BAR,
            PlotType.BAR_STACKED,
            PlotType.BAR_GROUPED,
            PlotType.BAR_HORIZONTAL,
            PlotType.LINE,
            PlotType.SCATTER,
            PlotType.SCATTER_3D,
            PlotType.BOX,
            PlotType.HISTOGRAM,
            PlotType.HEATMAP,
            PlotType.PIE,
            PlotType.AREA,
        ]
    
    def render(self, spec: PlotSpec) -> str:
        """
        Render a PlotSpec to an HTML div with ECharts.
        
        Args:
            spec: The plot specification
            
        Returns:
            HTML string with ECharts chart
        """
        if not self.supports(spec.plot_type):
            raise RenderError(
                f"Unsupported plot type: {spec.plot_type}",
                renderer=self.name,
                spec=spec
            )
        
        try:
            # Generate ECharts option
            option = self._spec_to_option(spec)
            
            # Generate unique chart ID
            chart_id = spec.plot_id or f"echarts_{uuid.uuid4().hex[:8]}"
            
            # Generate HTML with embedded ECharts
            html = self._generate_html(chart_id, option, spec)
            return html
            
        except Exception as e:
            logger.error(f"ECharts render error: {e}")
            raise RenderError(str(e), renderer=self.name, spec=spec)
    
    def _spec_to_option(self, spec: PlotSpec) -> Dict[str, Any]:
        """Convert PlotSpec to ECharts option object."""
        option = {
            "title": self._create_title(spec),
            "tooltip": self._create_tooltip(spec),
            "legend": self._create_legend(spec),
            "xAxis": self._create_x_axis(spec),
            "yAxis": self._create_y_axis(spec),
            "series": self._create_series(spec),
            "color": ULTRAQC_NEON_COLORS,
        }
        
        # Add grid for proper margins
        option["grid"] = {
            "left": spec.layout.margin.get("l", 80),
            "right": spec.layout.margin.get("r", 40),
            "top": spec.layout.margin.get("t", 80),
            "bottom": spec.layout.margin.get("b", 80),
            "containLabel": True,
        }
        
        # Add toolbox for interactivity
        option["toolbox"] = {
            "feature": {
                "saveAsImage": {},
                "dataZoom": {},
                "restore": {},
            }
        }
        
        return option
    
    def _create_title(self, spec: PlotSpec) -> Dict[str, Any]:
        """Create ECharts title config."""
        return {
            "text": spec.layout.title or "",
            "left": "center",
            "textStyle": {
                "fontSize": spec.style.title_font_size,
            }
        }
    
    def _create_tooltip(self, spec: PlotSpec) -> Dict[str, Any]:
        """Create ECharts tooltip config."""
        trigger = "axis" if spec.plot_type in (PlotType.LINE, PlotType.BAR) else "item"
        return {
            "trigger": trigger,
            "axisPointer": {"type": "shadow" if spec.plot_type == PlotType.BAR else "line"}
        }

    def _create_legend(self, spec: PlotSpec) -> Dict[str, Any]:
        """Create ECharts legend config."""
        if not spec.layout.show_legend:
            return {"show": False}

        position_map = {
            "right": {"orient": "vertical", "right": 10, "top": "center"},
            "left": {"orient": "vertical", "left": 10, "top": "center"},
            "top": {"orient": "horizontal", "top": 30, "left": "center"},
            "bottom": {"orient": "horizontal", "bottom": 10, "left": "center"},
        }
        return {"show": True, **position_map.get(spec.layout.legend_position, {})}

    def _create_x_axis(self, spec: PlotSpec) -> Dict[str, Any]:
        """Create ECharts x-axis config."""
        axis = spec.layout.x_axis

        # Get categories from data
        categories = None
        if spec.series and spec.series[0].x:
            categories = spec.series[0].x
        elif spec.data is not None and spec.x:
            categories = spec.data[spec.x].tolist()

        return {
            "type": "category" if categories else "value",
            "name": axis.title or "",
            "data": categories,
            "axisLine": {"show": axis.show_line},
            "splitLine": {"show": axis.show_grid},
        }

    def _create_y_axis(self, spec: PlotSpec) -> Dict[str, Any]:
        """Create ECharts y-axis config."""
        axis = spec.layout.y_axis
        return {
            "type": axis.type if axis.type != "linear" else "value",
            "name": axis.title or "",
            "axisLine": {"show": axis.show_line},
            "splitLine": {"show": axis.show_grid},
        }

    def _create_series(self, spec: PlotSpec) -> List[Dict[str, Any]]:
        """Create ECharts series config."""
        series_list = []

        if spec.series:
            for i, s in enumerate(spec.series):
                series_list.append(self._series_to_echarts(spec.plot_type, s, i))
        elif spec.data is not None:
            series_list.append(self._dataframe_to_echarts(spec))

        return series_list

    def _series_to_echarts(
        self,
        plot_type: PlotType,
        series: PlotSeries,
        index: int
    ) -> Dict[str, Any]:
        """Convert PlotSeries to ECharts series config."""
        type_map = {
            PlotType.BAR: "bar",
            PlotType.BAR_STACKED: "bar",
            PlotType.BAR_GROUPED: "bar",
            PlotType.BAR_HORIZONTAL: "bar",
            PlotType.LINE: "line",
            PlotType.SCATTER: "scatter",
            PlotType.PIE: "pie",
            PlotType.AREA: "line",
            PlotType.HEATMAP: "heatmap",
        }

        echarts_type = type_map.get(plot_type, "scatter")

        result = {
            "name": series.name,
            "type": echarts_type,
            "data": series.y if series.y else [],
        }

        # Handle stacking
        if plot_type == PlotType.BAR_STACKED:
            result["stack"] = "total"

        # Handle area fill
        if plot_type == PlotType.AREA:
            result["areaStyle"] = {}

        return result

    def _dataframe_to_echarts(self, spec: PlotSpec) -> Dict[str, Any]:
        """Convert DataFrame to ECharts series."""
        df = spec.data
        y_data = df[spec.y].tolist() if spec.y and spec.y in df.columns else []

        return {
            "name": spec.y or "Data",
            "type": "bar" if spec.plot_type == PlotType.BAR else "scatter",
            "data": y_data,
        }

    def _generate_html(
        self,
        chart_id: str,
        option: Dict[str, Any],
        spec: PlotSpec
    ) -> str:
        """Generate HTML with embedded ECharts."""
        option_json = json.dumps(option, indent=2)
        height = spec.layout.height
        width = spec.layout.width or "100%"

        html = f'''
        <div id="{chart_id}" style="width: {width}; height: {height}px;"></div>
        <script src="{self.ECHARTS_CDN}"></script>
        <script>
            (function() {{
                var chart = echarts.init(document.getElementById('{chart_id}'));
                var option = {option_json};
                chart.setOption(option);
                window.addEventListener('resize', function() {{
                    chart.resize();
                }});
            }})();
        </script>
        '''
        return html
