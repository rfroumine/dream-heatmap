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
/* ================================================================
   Layer 1 — CSS Custom Properties
   ================================================================ */
:root, :host {
  --design-primary-color: #1a73e8;
  --design-primary-text-color: #ffffff;
  --design-secondary-color: #1557b0;
  --design-surface-color: #ffffff;
  --design-background-color: #fafafa;
  --panel-primary-color: #1a73e8;
  --panel-secondary-color: #1557b0;
  --mdc-theme-primary: #1a73e8;
  --mdc-theme-secondary: #1557b0;
  --mdc-theme-surface: #ffffff;
  --mdc-shape-medium: 16px;
}

/* ================================================================
   Layer 2 — Component overrides (organic + Inter)
   ================================================================ */

/* ---- Pill buttons (primary + success) ---- */
.bk-btn-primary, .bk-btn-success {
  border-radius: 24px !important;
  background-color: #1a73e8 !important;
  border-color: #1a73e8 !important;
  color: #ffffff !important;
  box-shadow: none !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
}
.bk-btn-primary:hover, .bk-btn-success:hover {
  background-color: #1557b0 !important;
  border-color: #1557b0 !important;
}

/* ---- Outlined danger button ---- */
.bk-btn-danger {
  border-radius: 24px !important;
  background-color: transparent !important;
  border: 1px solid #d93025 !important;
  color: #d93025 !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  text-transform: none !important;
  box-shadow: none !important;
}
.bk-btn-danger:hover {
  background-color: rgba(217,48,37,0.08) !important;
}

/* ---- Toggle buttons (active state) ---- */
.bk-btn-default.active,
.bk-active {
  background-color: #e8f0fe !important;
  border-color: #1a73e8 !important;
  color: #1a73e8 !important;
}

/* ---- Input / select widgets ---- */
.bk-input, select {
  border-radius: 10px !important;
  border: 1px solid #dadce0 !important;
  font-size: 13px !important;
  padding: 5px 8px !important;
}
.bk-input:focus, select:focus {
  border-color: #1a73e8 !important;
  box-shadow: 0 0 0 2px rgba(26,115,232,0.2) !important;
}

/* ---- Radio button group ---- */
.bk-btn-group .bk-btn {
  font-size: 11px !important;
  border-radius: 4px !important;
  text-transform: none !important;
}

/* ---- Cards ---- */
.card {
  border-radius: 16px !important;
  border: none !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08),
              0 1px 2px rgba(0,0,0,0.06) !important;
  margin-bottom: 8px !important;
}
.card-header {
  background: transparent !important;
  border-bottom: none !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 12px 16px !important;
}

/* ---- Labels ---- */
label, .bk-input-group label {
  font-size: 12px !important;
  font-weight: 500 !important;
}

/* ---- Divider ---- */
.bk-Divider {
  border-top: 1px solid #f0f0f0 !important;
  margin: 8px 0 !important;
}

/* ================================================================
   Layer 3 — Template-level CSS
   ================================================================ */

/* ---- Inter font ---- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
body, .mdc-typography {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
  color: #202124 !important;
}

/* ---- Compact header ---- */
.mdc-top-app-bar {
  height: 44px !important;
  min-height: 44px !important;
  background: #fafafa !important;
  box-shadow: none !important;
  border-bottom: 1px solid #f0f0f0 !important;
}
.mdc-top-app-bar__title {
  font-size: 14px !important;
  font-weight: 500 !important;
  color: #202124 !important;
  letter-spacing: -0.01em !important;
}
.mdc-top-app-bar__row {
  height: 44px !important;
  min-height: 44px !important;
}
.mdc-top-app-bar--fixed-adjust {
  padding-top: 44px !important;
}

/* ---- Header icon visibility ---- */
.mdc-top-app-bar .mdc-icon-button,
.mdc-top-app-bar .mdc-top-app-bar__navigation-icon,
.mdc-top-app-bar .mdc-top-app-bar__action-item {
  color: #202124 !important;
}

/* ---- Organic sidebar (shadow, no hard border) ---- */
#sidebar {
  background: #fafafa !important;
  border-right: none !important;
  box-shadow: 1px 0 3px rgba(0,0,0,0.04) !important;
}
#sidebar .mdc-drawer__content { background: #fafafa !important; }

/* ---- Main content area ---- */
.main .bk-Column {
  padding: 12px !important;
}

/* ---- Code export modal ---- */
.code-export-modal pre {
  background: #1e1e2e !important;
  color: #cdd6f4 !important;
  border-radius: 16px !important;
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

        # Inject custom CSS and loading spinner color
        pn.config.raw_css.append(_DASHBOARD_CSS)
        pn.config.loading_color = "#1a73e8"

        # Create the heatmap pane (JSComponent)
        self.heatmap_pane = HeatmapPane(
            sizing_mode="stretch_width",
            min_height=250,
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

        # Chart layout container (bottom grid only)
        self._bottom_chart_grid = pn.GridBox(
            ncols=2,
            visible=False,
            css_classes=["hm-bottom-charts"],
            sizing_mode="stretch_width",
        )

        # Build chart manager and sidebar
        self.chart_manager = ChartPanelManager(
            self.state,
            bottom_grid=self._bottom_chart_grid,
        )
        self.sidebar_controls = SidebarControls(self.state, chart_manager=self.chart_manager)

        # Trigger initial render
        self.state.trigger_rebuild()

    def _build_template(self) -> pn.template.MaterialTemplate:
        """Build the Panel MaterialTemplate layout."""
        template = pn.template.MaterialTemplate(
            title="dream heatmap",
            sidebar=[self.sidebar_controls.build_panel()],
            sidebar_width=260,
            header_background="#fafafa",
            header_color="#202124",
        )

        # Wire sidebar → template for modal support
        self.sidebar_controls.set_template(template)
        template.modal.extend(self.sidebar_controls.build_modal_content())

        # Main content: full-width heatmap + bottom chart grid
        main_content = pn.Column(
            self.heatmap_pane,
            self._bottom_chart_grid,
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
