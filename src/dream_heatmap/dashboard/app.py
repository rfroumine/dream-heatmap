"""DashboardApp: assembles the Panel template and serves the dashboard."""

from __future__ import annotations

import panel as pn
import pandas as pd

from .state import DashboardState
from .heatmap_pane import HeatmapPane
from .sidebar import SidebarControls
from .chart_panel import ChartPanelManager


class DashboardApp:
    """Interactive heatmap dashboard application.

    Assembles a Panel MaterialTemplate with:
    - Sidebar: heatmap configuration controls
    - Main area: D3/canvas heatmap + Plotly analysis charts
    - Selection bridge: JS selection → Python → chart updates
    """

    def __init__(
        self,
        data: pd.DataFrame,
        row_metadata: pd.DataFrame | None = None,
        col_metadata: pd.DataFrame | None = None,
    ) -> None:
        pn.extension("plotly", sizing_mode="stretch_width")

        # Create the heatmap pane (JSComponent)
        self.heatmap_pane = HeatmapPane(
            sizing_mode="stretch_width",
            min_height=400,
        )

        # Create centralized state
        self.state = DashboardState(
            data=data,
            row_metadata=row_metadata,
            col_metadata=col_metadata,
            _heatmap_pane=self.heatmap_pane,
        )

        # Wire selection bridge: JS → HeatmapPane.selection_json → state
        self.heatmap_pane.param.watch(
            lambda event: self.state.update_selection(event.new),
            "selection_json",
        )

        # Build sidebar and chart panel
        self.sidebar_controls = SidebarControls(self.state)
        self.chart_manager = ChartPanelManager(self.state)

        # Trigger initial render
        self.state.trigger_rebuild()

    def _build_template(self) -> pn.template.MaterialTemplate:
        """Build the Panel MaterialTemplate layout."""
        template = pn.template.MaterialTemplate(
            title="dream-heatmap Explorer",
            sidebar=[self.sidebar_controls.build_panel()],
            sidebar_width=300,
        )

        # Main content area
        main_content = pn.Column(
            self.heatmap_pane,
            pn.layout.Divider(),
            self.chart_manager.build_panel(),
            sizing_mode="stretch_width",
        )
        template.main.append(main_content)

        return template

    def serve(self, port: int = 0, show: bool = True, **kwargs) -> None:
        """Start the Panel server and optionally open the browser.

        Parameters
        ----------
        port : int
            Port number. 0 = auto-assign.
        show : bool
            Whether to open the browser automatically.
        **kwargs
            Additional keyword arguments passed to pn.serve().
        """
        template = self._build_template()
        pn.serve(
            template,
            port=port or 0,
            show=show,
            title="dream-heatmap Explorer",
            **kwargs,
        )
