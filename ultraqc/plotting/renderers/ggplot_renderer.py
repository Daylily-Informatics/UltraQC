# -*- coding: utf-8 -*-
"""
GGPlotRenderer - Grammar of Graphics visualization backend using plotnine.

This renderer provides ggplot2-style plotting for users who prefer
the grammar of graphics approach to data visualization.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Any, Dict, List, Optional

from ultraqc.plotting.base import PlotRenderer, RenderError
from ultraqc.plotting.spec import (
    PlotSpec, PlotType, PlotSeries, PlotMode, PlotLayout, PlotStyle
)

logger = logging.getLogger(__name__)


# UltraQC neon theme colors for ggplot
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


class GGPlotRenderer(PlotRenderer):
    """
    plotnine (ggplot2) rendering backend.
    
    This renderer provides grammar of graphics style plotting,
    which is particularly useful for statistical visualizations
    and publication-quality figures.
    """
    
    name = "ggplot"
    description = "Grammar of graphics style using plotnine"
    version = "1.0.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        super().__init__(config)
        self._plotnine = None
        self._pd = None
    
    def _validate_dependencies(self) -> None:
        """Validate plotnine is available."""
        try:
            import plotnine
            import pandas as pd
            self._plotnine = plotnine
            self._pd = pd
        except ImportError:
            raise ImportError(
                "plotnine is required for GGPlotRenderer. "
                "Install with: pip install plotnine"
            )
    
    @property
    def supported_plot_types(self) -> List[PlotType]:
        """Plot types supported by plotnine."""
        return [
            PlotType.BAR,
            PlotType.BAR_STACKED,
            PlotType.BAR_GROUPED,
            PlotType.BAR_HORIZONTAL,
            PlotType.LINE,
            PlotType.SCATTER,
            PlotType.BOX,
            PlotType.VIOLIN,
            PlotType.HISTOGRAM,
            PlotType.AREA,
        ]
    
    def render(self, spec: PlotSpec) -> str:
        """
        Render a PlotSpec to an HTML img tag with embedded PNG.
        
        Args:
            spec: The plot specification
            
        Returns:
            HTML string with embedded image
        """
        if not self.supports(spec.plot_type):
            raise RenderError(
                f"Unsupported plot type: {spec.plot_type}",
                renderer=self.name,
                spec=spec
            )
        
        try:
            # Create the ggplot figure
            p = self._spec_to_ggplot(spec)
            
            # Render to PNG in memory
            buf = io.BytesIO()
            p.save(buf, format="png", dpi=150, verbose=False)
            buf.seek(0)
            
            # Encode as base64 and create HTML
            img_data = base64.b64encode(buf.read()).decode("utf-8")
            html = f'''
            <div class="ggplot-container" style="text-align: center;">
                <img src="data:image/png;base64,{img_data}" 
                     alt="{spec.layout.title or 'Plot'}"
                     style="max-width: 100%; height: auto;" />
            </div>
            '''
            return html
            
        except Exception as e:
            logger.error(f"GGPlot render error: {e}")
            raise RenderError(str(e), renderer=self.name, spec=spec)
    
    def _spec_to_ggplot(self, spec: PlotSpec):
        """Convert PlotSpec to plotnine ggplot object."""
        from plotnine import (
            ggplot, aes, geom_bar, geom_line, geom_point, geom_boxplot,
            geom_violin, geom_histogram, geom_area, coord_flip,
            labs, theme_minimal, theme, element_text, element_rect,
            scale_fill_manual, scale_color_manual
        )
        
        # Prepare data
        df = self._prepare_dataframe(spec)
        
        # Build aesthetic mapping
        aes_mapping = self._build_aes(spec)
        
        # Start building the plot
        p = ggplot(df, aes_mapping)
        
        # Add geometry based on plot type
        p = self._add_geometry(p, spec)
        
        # Add labels
        p = p + labs(
            title=spec.layout.title or "",
            x=spec.layout.x_axis.title or spec.x or "",
            y=spec.layout.y_axis.title or spec.y or "",
        )
        
        # Apply theme
        p = self._apply_theme(p, spec)
        
        return p
    
    def _prepare_dataframe(self, spec: PlotSpec):
        """Prepare DataFrame for plotting."""
        if spec.data is not None:
            return spec.data.copy()

        # Build DataFrame from series
        import pandas as pd
        data = []
        for series in spec.series:
            if series.x and series.y:
                for i, (x, y) in enumerate(zip(series.x, series.y)):
                    data.append({
                        "x": x,
                        "y": y,
                        "series": series.name,
                    })
        return pd.DataFrame(data)

    def _build_aes(self, spec: PlotSpec):
        """Build aesthetic mapping."""
        from plotnine import aes

        aes_kwargs = {}

        if spec.x:
            aes_kwargs["x"] = spec.x
        elif spec.series:
            aes_kwargs["x"] = "x"

        if spec.y:
            aes_kwargs["y"] = spec.y
        elif spec.series:
            aes_kwargs["y"] = "y"

        if spec.color:
            aes_kwargs["color"] = spec.color
            aes_kwargs["fill"] = spec.color
        elif spec.group:
            aes_kwargs["color"] = spec.group
            aes_kwargs["fill"] = spec.group
        elif spec.series and len(spec.series) > 1:
            aes_kwargs["color"] = "series"
            aes_kwargs["fill"] = "series"

        return aes(**aes_kwargs)

    def _add_geometry(self, p, spec: PlotSpec):
        """Add appropriate geometry to the plot."""
        from plotnine import (
            geom_bar, geom_line, geom_point, geom_boxplot,
            geom_violin, geom_histogram, geom_area, coord_flip
        )

        if spec.plot_type == PlotType.BAR:
            p = p + geom_bar(stat="identity")
        elif spec.plot_type == PlotType.BAR_STACKED:
            p = p + geom_bar(stat="identity", position="stack")
        elif spec.plot_type == PlotType.BAR_GROUPED:
            p = p + geom_bar(stat="identity", position="dodge")
        elif spec.plot_type == PlotType.BAR_HORIZONTAL:
            p = p + geom_bar(stat="identity") + coord_flip()
        elif spec.plot_type == PlotType.LINE:
            p = p + geom_line()
        elif spec.plot_type == PlotType.SCATTER:
            p = p + geom_point()
        elif spec.plot_type == PlotType.BOX:
            p = p + geom_boxplot()
        elif spec.plot_type == PlotType.VIOLIN:
            p = p + geom_violin()
        elif spec.plot_type == PlotType.HISTOGRAM:
            p = p + geom_histogram(bins=spec.nbins)
        elif spec.plot_type == PlotType.AREA:
            p = p + geom_area()

        return p

    def _apply_theme(self, p, spec: PlotSpec):
        """Apply UltraQC theme to the plot."""
        from plotnine import (
            theme_minimal, theme, element_text, element_rect,
            scale_fill_manual, scale_color_manual
        )

        # Apply minimal theme as base
        p = p + theme_minimal()

        # Apply UltraQC colors
        p = p + scale_fill_manual(values=ULTRAQC_NEON_COLORS)
        p = p + scale_color_manual(values=ULTRAQC_NEON_COLORS)

        # Custom theme adjustments
        p = p + theme(
            plot_title=element_text(size=14, face="bold"),
            axis_title=element_text(size=12),
            legend_position="right" if spec.layout.show_legend else "none",
        )

        return p

    def render_to_image(self, spec: PlotSpec, format: str = "png") -> bytes:
        """Render plot to static image."""
        p = self._spec_to_ggplot(spec)
        buf = io.BytesIO()
        p.save(buf, format=format, dpi=150, verbose=False)
        buf.seek(0)
        return buf.read()
