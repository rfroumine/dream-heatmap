"""DashboardApp: assembles the Panel template and serves the dashboard."""

from __future__ import annotations

import panel as pn
import pandas as pd

from .state import DashboardState
from .heatmap_pane import HeatmapPane
from .sidebar import SidebarControls
from .chart_panel import ChartPanelManager

# ---------------------------------------------------------------------------
# Custom CSS — Notion/Linear-inspired visual polish
# ---------------------------------------------------------------------------

_DASHBOARD_CSS = """
/* ---- Typography ---- */
body, .mdc-typography {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter",
               "Roboto", "Helvetica Neue", Arial, sans-serif !important;
}

/* ---- Sidebar ---- */
#sidebar {
  background: #f9fafb !important;
  border-right: 1px solid #e5e7eb !important;
  padding: 12px 16px !important;
}
#sidebar .mdc-drawer__content {
  background: #f9fafb !important;
}

/* ---- Sidebar section headers ---- */
#sidebar h2, #sidebar .markdown h2 {
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #6b7280 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
  margin-bottom: 8px !important;
}

/* ---- Widget labels ---- */
#sidebar label, #sidebar .bk-input-group label {
  font-size: 12px !important;
  font-weight: 500 !important;
  color: #374151 !important;
}

/* ---- Cards ---- */
#sidebar .card {
  border-radius: 8px !important;
  border: 1px solid #e5e7eb !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
  background: #ffffff !important;
  margin-bottom: 8px !important;
  overflow: hidden !important;
}
#sidebar .card-header {
  background: transparent !important;
  border-bottom: 1px solid #f3f4f6 !important;
  padding: 8px 12px !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  color: #374151 !important;
}
#sidebar .card-body, #sidebar .card .bk-Column {
  padding: 8px 12px !important;
}

/* ---- Buttons ---- */
#sidebar .bk-btn-primary {
  border-radius: 6px !important;
  background-color: #6366f1 !important;
  border-color: #6366f1 !important;
  color: #ffffff !important;
  font-weight: 500 !important;
  font-size: 12px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  box-shadow: 0 1px 2px rgba(99,102,241,0.2) !important;
}
#sidebar .bk-btn-primary:hover {
  background-color: #4f46e5 !important;
  border-color: #4f46e5 !important;
}

/* Export button special styling */
#sidebar .bk-btn-success {
  border-radius: 6px !important;
  background-color: #6366f1 !important;
  border-color: #6366f1 !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  box-shadow: 0 1px 3px rgba(99,102,241,0.3) !important;
  padding: 8px 16px !important;
}
#sidebar .bk-btn-success:hover {
  background-color: #4f46e5 !important;
  border-color: #4f46e5 !important;
}

#sidebar .bk-btn-danger {
  border-radius: 6px !important;
  font-size: 11px !important;
  text-transform: none !important;
}

/* ---- Toggle buttons (active state) ---- */
#sidebar .bk-btn-default.active,
#sidebar .bk-active {
  background-color: #eff6ff !important;
  border-color: #6366f1 !important;
  color: #6366f1 !important;
}

/* ---- Select / Input widgets ---- */
#sidebar select, #sidebar .bk-input {
  border-radius: 6px !important;
  border: 1px solid #d1d5db !important;
  font-size: 12px !important;
  padding: 5px 8px !important;
}
#sidebar select:focus, #sidebar .bk-input:focus {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 2px rgba(99,102,241,0.15) !important;
}

/* ---- Radio button group ---- */
#sidebar .bk-btn-group .bk-btn {
  font-size: 11px !important;
  border-radius: 4px !important;
  text-transform: none !important;
}

/* ---- Spacing ---- */
#sidebar .bk-Column > div {
  margin-bottom: 4px !important;
}

/* ---- Header bar ---- */
.mdc-top-app-bar {
  background-color: #ffffff !important;
  border-bottom: 1px solid #e5e7eb !important;
  box-shadow: none !important;
}
.mdc-top-app-bar .mdc-top-app-bar__title {
  color: #111827 !important;
  font-weight: 600 !important;
  font-size: 16px !important;
}

/* ---- Main content area ---- */
.main .bk-Column {
  padding: 16px !important;
}

/* ---- Divider ---- */
.bk-Divider {
  border-top: 1px solid #e5e7eb !important;
  margin: 8px 0 !important;
}

/* ---- Code export modal ---- */
.code-export-modal pre {
  background: #1e1e2e !important;
  color: #cdd6f4 !important;
  border-radius: 8px !important;
  padding: 16px !important;
  font-size: 12px !important;
  line-height: 1.5 !important;
  overflow-x: auto !important;
  font-family: "Fira Code", "JetBrains Mono", "Cascadia Code", monospace !important;
}
"""


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

        # Inject custom CSS
        pn.config.raw_css.append(_DASHBOARD_CSS)

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

        # Wire zoom bridge: JS → HeatmapPane.zoom_range_json → state
        self.heatmap_pane.param.watch(
            lambda event: self.state.handle_zoom(event.new),
            "zoom_range_json",
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
            sidebar_width=320,
            header_background="#ffffff",
            header_color="#111827",
        )

        # Wire sidebar → template for modal support
        self.sidebar_controls.set_template(template)
        template.modal.extend(self.sidebar_controls.build_modal_content())

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
