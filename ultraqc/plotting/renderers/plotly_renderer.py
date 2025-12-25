# -*- coding: utf-8 -*-
"""
PlotlyRenderer - Default visualization backend using Plotly.js.

This renderer maintains full backward compatibility with the existing
UltraQC plotting functionality while conforming to the plugin interface.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import plotly.figure_factory as ff
import plotly.graph_objs as go
import plotly.offline as py

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


class PlotlyRenderer(PlotRenderer):
    """
    Plotly.js rendering backend.
    
    This is the default renderer for UltraQC, providing interactive
    charts with full feature parity with the original implementation.
    """
    
    name = "plotly"
    description = "Interactive charts using Plotly.js"
    version = "1.0.0"
    
    def _validate_dependencies(self) -> None:
        """Validate Plotly is available."""
        try:
            import plotly
        except ImportError:
            raise ImportError(
                "Plotly is required for PlotlyRenderer. "
                "Install with: pip install plotly"
            )
    
    @property
    def supported_plot_types(self) -> List[PlotType]:
        """All plot types are supported by Plotly."""
        return list(PlotType)
    
    def render(self, spec: PlotSpec) -> str:
        """
        Render a PlotSpec to an HTML div containing the Plotly chart.
        
        Args:
            spec: The plot specification
            
        Returns:
            HTML string with the rendered plot
        """
        if not self.supports(spec.plot_type):
            raise RenderError(
                f"Unsupported plot type: {spec.plot_type}",
                renderer=self.name,
                spec=spec
            )
        
        try:
            # Convert PlotSpec to Plotly figure
            fig = self._spec_to_figure(spec)
            
            # Render to HTML div
            config = self._get_plotly_config(spec)
            html = py.plot(
                fig,
                output_type="div",
                show_link=False,
                config=config,
            )
            return html
            
        except Exception as e:
            logger.error(f"Plotly render error: {e}")
            raise RenderError(str(e), renderer=self.name, spec=spec)
    
    def _spec_to_figure(self, spec: PlotSpec) -> go.Figure:
        """Convert PlotSpec to Plotly Figure."""
        traces = self._create_traces(spec)
        layout = self._create_layout(spec)
        return go.Figure(data=traces, layout=layout)
    
    def _create_traces(self, spec: PlotSpec) -> List[Any]:
        """Create Plotly traces from PlotSpec."""
        traces = []
        
        # Use series if provided, otherwise convert from DataFrame
        if spec.series:
            for i, series in enumerate(spec.series):
                trace = self._series_to_trace(spec.plot_type, series, i)
                if trace is not None:
                    traces.append(trace)
        elif spec.data is not None:
            traces = self._dataframe_to_traces(spec)
        
        return traces
    
    def _series_to_trace(
        self, 
        plot_type: PlotType, 
        series: PlotSeries, 
        index: int
    ) -> Optional[Any]:
        """Convert a PlotSeries to a Plotly trace."""
        color = self._get_series_color(series, index)
        
        if plot_type == PlotType.BAR or plot_type == PlotType.BAR_STACKED:
            return go.Bar(
                x=series.x,
                y=series.y,
                name=series.name,
                text=series.text,
                visible=series.visible,
                marker=dict(color=color),
                hoverinfo="text+x+y" if series.text else "x+y",
                **series.options
            )
        
        elif plot_type == PlotType.BAR_HORIZONTAL:
            return go.Bar(
                x=series.y,  # Swapped for horizontal
                y=series.x,
                name=series.name,
                text=series.text,
                orientation="h",
                visible=series.visible,
                marker=dict(color=color),
                hoverinfo="text+x+y" if series.text else "x+y",
                **series.options
            )
        
        elif plot_type in (PlotType.LINE, PlotType.SCATTER):
            mode = self._mode_to_plotly(series.mode)
            return go.Scatter(
                x=series.x,
                y=series.y,
                name=series.name,
                text=series.text,
                mode=mode,
                visible=series.visible,
                marker=dict(color=color),
                line=dict(color=color),
                hoverinfo="text+x+y" if series.text else "x+y",
                **series.options
            )
        
        elif plot_type == PlotType.SCATTER_3D:
            return go.Scatter3d(
                x=series.x,
                y=series.y,
                z=series.z,
                name=series.name,
                text=series.text,
                mode="markers",
                visible=series.visible,
                marker=dict(color=color, opacity=0.8),
                **series.options
            )

        elif plot_type == PlotType.BOX:
            return go.Box(
                y=series.y,
                name=series.name,
                visible=series.visible,
                marker=dict(color=color),
                **series.options
            )

        elif plot_type == PlotType.HISTOGRAM:
            return go.Histogram(
                x=series.x if series.x else series.y,
                name=series.name,
                opacity=0.75,
                visible=series.visible,
                marker=dict(color=color),
                **series.options
            )

        elif plot_type == PlotType.VIOLIN:
            # Violin plots need special handling via figure_factory
            return None  # Handled separately

        else:
            logger.warning(f"Unsupported plot type for series: {plot_type}")
            return None

    def _dataframe_to_traces(self, spec: PlotSpec) -> List[Any]:
        """Convert DataFrame-based PlotSpec to traces."""
        traces = []
        df = spec.data

        if df is None or df.empty:
            return traces

        # Group by if specified
        if spec.group and spec.group in df.columns:
            for i, (group_name, group_df) in enumerate(df.groupby(spec.group)):
                color = self._get_color_by_index(i)
                trace = self._create_trace_from_df(
                    spec.plot_type, group_df, spec, str(group_name), color
                )
                if trace:
                    traces.append(trace)
        else:
            trace = self._create_trace_from_df(
                spec.plot_type, df, spec, "Data", self._get_color_by_index(0)
            )
            if trace:
                traces.append(trace)

        return traces

    def _create_trace_from_df(
        self,
        plot_type: PlotType,
        df: "pd.DataFrame",
        spec: PlotSpec,
        name: str,
        color: str
    ) -> Optional[Any]:
        """Create a single trace from DataFrame."""
        x = df[spec.x].tolist() if spec.x and spec.x in df.columns else None
        y = df[spec.y].tolist() if spec.y and spec.y in df.columns else None
        z = df[spec.z].tolist() if spec.z and spec.z in df.columns else None
        text = df[spec.text].tolist() if spec.text and spec.text in df.columns else None

        series = PlotSeries(
            name=name,
            x=x,
            y=y,
            z=z,
            text=text,
            mode=PlotMode.MARKERS,
        )
        return self._series_to_trace(plot_type, series, 0)

    def _create_layout(self, spec: PlotSpec) -> go.Layout:
        """Create Plotly layout from PlotSpec."""
        layout_dict = {
            "title": spec.layout.title,
            "height": spec.layout.height,
            "margin": spec.layout.margin,
            "showlegend": spec.layout.show_legend,
            "hovermode": spec.layout.hover_mode,
        }

        if spec.layout.width:
            layout_dict["width"] = spec.layout.width

        # X-axis
        layout_dict["xaxis"] = self._axis_to_dict(spec.layout.x_axis)

        # Y-axis
        layout_dict["yaxis"] = self._axis_to_dict(spec.layout.y_axis)

        # Z-axis for 3D plots
        if spec.plot_type == PlotType.SCATTER_3D and spec.layout.z_axis:
            layout_dict["scene"] = {
                "xaxis": self._axis_to_dict(spec.layout.x_axis),
                "yaxis": self._axis_to_dict(spec.layout.y_axis),
                "zaxis": self._axis_to_dict(spec.layout.z_axis),
            }

        # Bar mode
        if spec.plot_type in (PlotType.BAR_STACKED, PlotType.BAR_GROUPED, PlotType.BAR):
            layout_dict["barmode"] = spec.layout.bar_mode

        # Annotations
        if spec.layout.annotations:
            layout_dict["annotations"] = spec.layout.annotations

        # Shapes
        if spec.layout.shapes:
            layout_dict["shapes"] = spec.layout.shapes

        return go.Layout(**layout_dict)

    def _axis_to_dict(self, axis) -> Dict[str, Any]:
        """Convert AxisConfig to Plotly dict."""
        if axis is None:
            return {}
        return {
            "title": axis.title,
            "type": axis.type,
            "showgrid": axis.show_grid,
            "showline": axis.show_line,
            "zeroline": axis.zero_line,
        }

    def _get_plotly_config(self, spec: PlotSpec) -> Dict[str, Any]:
        """Get Plotly config options."""
        return {
            "displaylogo": False,
            "modeBarButtonsToRemove": spec.mode_bar_buttons_to_remove,
        }

    def _mode_to_plotly(self, mode: PlotMode) -> str:
        """Convert PlotMode to Plotly mode string."""
        mapping = {
            PlotMode.MARKERS: "markers",
            PlotMode.LINES: "lines",
            PlotMode.LINES_MARKERS: "lines+markers",
        }
        return mapping.get(mode, "markers")

    def _get_series_color(self, series: PlotSeries, index: int) -> str:
        """Get color for a series."""
        if series.style and series.style.color:
            return series.style.color
        return self._get_color_by_index(index)

    def _get_color_by_index(self, index: int) -> str:
        """Get color from UltraQC neon palette."""
        return ULTRAQC_NEON_COLORS[index % len(ULTRAQC_NEON_COLORS)]

    def render_violin(self, data: Dict[str, List[float]]) -> str:
        """
        Render a violin plot using Plotly figure_factory.

        This is a special case as Plotly handles violin plots differently.

        Args:
            data: Dictionary mapping names to data arrays

        Returns:
            HTML string
        """
        try:
            fig = ff.create_violin(data)
            return py.plot(
                fig,
                output_type="div",
                show_link=False,
                config={"displaylogo": False},
            )
        except Exception as e:
            logger.error(f"Violin plot error: {e}")
            raise RenderError(str(e), renderer=self.name)

    def render_to_image(self, spec: PlotSpec, format: str = "png") -> bytes:
        """Render plot to static image."""
        try:
            import plotly.io as pio
            fig = self._spec_to_figure(spec)
            return pio.to_image(fig, format=format)
        except ImportError:
            raise NotImplementedError(
                "Static image export requires kaleido. "
                "Install with: pip install kaleido"
            )

