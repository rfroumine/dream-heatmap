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
   Layer 1 — CSS Custom Properties (Shopify Polaris / Indigo)
   ================================================================ */
:root, :host {
  --design-primary-color: #5c6ac4;
  --design-primary-text-color: #ffffff;
  --design-secondary-color: #4959bd;
  --design-surface-color: #ffffff;
  --design-background-color: #ffffff;
  --panel-primary-color: #5c6ac4;
  --panel-secondary-color: #4959bd;
  --mdc-theme-primary: #5c6ac4;
  --mdc-theme-secondary: #4959bd;
  --mdc-theme-surface: #ffffff;
  --mdc-shape-medium: 10px;
}

/* ================================================================
   Layer 2 — Component overrides (Shopify Admin + Outfit)
   ================================================================ */

/* ---- Pill buttons (primary + success) ---- */
.bk-btn-primary, .bk-btn-success {
  border-radius: 24px !important;
  background-color: #5c6ac4 !important;
  border-color: #5c6ac4 !important;
  color: #ffffff !important;
  box-shadow: none !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  transition: all 0.15s ease !important;
}
.bk-btn-primary:hover, .bk-btn-success:hover {
  background-color: #4959bd !important;
  border-color: #4959bd !important;
}

/* ---- Outlined danger button ---- */
.bk-btn-danger {
  border-radius: 24px !important;
  background-color: transparent !important;
  border: 1px solid #dc2626 !important;
  color: #dc2626 !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  text-transform: none !important;
  box-shadow: none !important;
  transition: all 0.15s ease !important;
}
.bk-btn-danger:hover {
  background-color: rgba(220,38,38,0.08) !important;
}

/* ---- Toggle buttons (active state) ---- */
.bk-btn-default.active,
.bk-active {
  background-color: rgba(92,106,196,0.06) !important;
  border-color: #5c6ac4 !important;
  color: #5c6ac4 !important;
}

/* ---- Input / select widgets ---- */
.bk-input, select {
  border-radius: 8px !important;
  border: 1px solid #c9cccf !important;
  font-size: 13px !important;
  padding: 5px 8px !important;
  transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
.bk-input:focus, select:focus {
  border-color: #5c6ac4 !important;
  box-shadow: 0 0 0 2px rgba(92,106,196,0.15) !important;
}

/* ---- Radio button group ---- */
.bk-btn-group .bk-btn {
  font-size: 11px !important;
  border-radius: 4px !important;
  text-transform: none !important;
}

/* ---- Flat icon buttons (light) ---- */
.bk-btn-light {
  background: none !important;
  border: none !important;
  box-shadow: none !important;
  padding: 2px !important;
  min-width: 0 !important;
  min-height: 0 !important;
  font-size: 14px !important;
  line-height: 1 !important;
  color: #94a3b8 !important;
  border-radius: 4px !important;
  cursor: pointer !important;
  transition: all 0.12s ease !important;
}
.bk-btn-light:hover:not(:disabled) {
  background: #e2e8f0 !important;
  color: #475569 !important;
}
.bk-btn-light:disabled {
  opacity: 0.25 !important;
  cursor: default !important;
}

/* ---- Labels ---- */
label, .bk-input-group label {
  font-size: 12px !important;
  font-weight: 500 !important;
  color: #637381 !important;
}

/* ---- Divider ---- */
.bk-Divider {
  border-top: 1px solid #e1e3e5 !important;
  margin: 8px 0 !important;
}

/* ================================================================
   Layer 3 — Template-level CSS
   ================================================================ */

/* ---- Outfit + JetBrains Mono fonts ---- */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
body, .mdc-typography {
  font-family: "Outfit", system-ui, -apple-system, sans-serif !important;
  color: #202223 !important;
}

/* ---- Hide header bar entirely ---- */
.mdc-top-app-bar {
  display: none !important;
}
.mdc-top-app-bar--fixed-adjust {
  padding-top: 0 !important;
}
.mdc-drawer {
  top: 0 !important;
}

/* ---- Loading spinner: more visible ---- */
.pn-loading.arcs::before {
  width: 48px !important;
  height: 48px !important;
  border-width: 4px !important;
}

/* ---- Clean white sidebar ---- */
#sidebar {
  background: #ffffff !important;
  border-right: 1px solid #e1e3e5 !important;
  box-shadow: none !important;
}
#sidebar .mdc-drawer__content { background: #ffffff !important; }
#sidebar .bk-input-group {
  margin-bottom: 4px !important;
}

/* ---- Main content area ---- */
.main .bk-Column {
  padding: 12px !important;
}

/* ---- Code export modal ---- */
.code-export-modal pre {
  background: #1e1e2e !important;
  color: #cdd6f4 !important;
  border-radius: 10px !important;
  padding: 16px !important;
  font-size: 12px !important;
  line-height: 1.5 !important;
  overflow-x: auto !important;
  font-family: "JetBrains Mono", "Cascadia Code", "Consolas", monospace !important;
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
        pn.config.loading_color = "#5c6ac4"

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
            title="dream-heatmap",
            sidebar=[self.sidebar_controls.build_panel()],
            sidebar_width=260,
            header_background="#ffffff",
            header_color="#1a1a2e",
        )

        # Wire sidebar → template for modal support
        self.sidebar_controls.set_template(template)
        template.modal.extend(self.sidebar_controls.build_modal_content())

        # Attribution line below the heatmap
        attribution = pn.pane.HTML(
            '<div style="text-align:right;font-size:11px;color:#919eab;'
            'padding:2px 8px 0 0;">Generated by dream-heatmap</div>',
            sizing_mode="stretch_width",
        )

        # Main content: full-width heatmap + attribution + bottom chart grid
        main_content = pn.Column(
            self.heatmap_pane,
            attribution,
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
