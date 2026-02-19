"""ChartPanelManager: manages a dynamic collection of Plotly analysis charts."""

from __future__ import annotations

import param
import panel as pn
import pandas as pd

from .state import DashboardState
from . import plotly_charts


CHART_TYPES = ["box", "violin", "bar", "scatter", "histogram"]


class ChartPanelManager:
    """Manages the chart panel below the heatmap.

    Users add charts via the "+ Add chart" bar. Each chart shows
    "All" (gray) vs "Selected" (highlighted) traces that update
    when the selection changes.
    """

    def __init__(self, state: DashboardState) -> None:
        self.state = state
        self._chart_panes: list[pn.Card] = []
        self._charts_container = pn.FlexBox(
            sizing_mode="stretch_width",
            flex_wrap="wrap",
            min_height=50,
        )

        # Build the add-chart controls
        self._build_add_bar()

        # Watch for selection changes to update charts
        state.param.watch(self._on_selection_change, ["selected_row_ids", "selected_col_ids"])

    def _build_add_bar(self) -> None:
        """Build the '+ Add chart' control bar."""
        self.chart_type_select = pn.widgets.Select(
            name="Type", options=CHART_TYPES, value="box",
            width=100,
        )
        self.chart_column_select = pn.widgets.Select(
            name="Column", options=self._get_chart_columns(),
            width=150,
        )
        # For scatter: second column
        self.chart_y_column_select = pn.widgets.Select(
            name="Y Column", options=self._get_chart_columns(),
            width=120, visible=False,
        )
        self.chart_add_button = pn.widgets.Button(
            name="+ Add chart", button_type="primary",
            width=100,
        )

        self.chart_add_button.on_click(self._on_add_chart)
        self.chart_type_select.param.watch(self._on_type_change, "value")

    def _get_chart_columns(self) -> list[str]:
        """Get available columns for chart data.

        Combines expression row names (markers) and metadata columns.
        """
        cols = []
        cols.extend(self.state.get_expression_row_names())
        cols.extend(self.state.get_col_metadata_columns())
        return cols

    def _on_type_change(self, event) -> None:
        """Show/hide the Y column selector for scatter charts."""
        self.chart_y_column_select.visible = (event.new == "scatter")

    def _on_add_chart(self, event) -> None:
        """Add a new chart to the panel."""
        chart_type = self.chart_type_select.value
        column = self.chart_column_select.value
        if not column:
            return

        cfg = {
            "type": chart_type,
            "column": column,
        }
        if chart_type == "scatter":
            cfg["y_column"] = self.chart_y_column_select.value or column

        # Append to state
        self.state.chart_configs = self.state.chart_configs + [cfg]
        self._rebuild_charts()

    def _on_remove_chart(self, index: int) -> None:
        """Remove a chart by index."""
        cfgs = list(self.state.chart_configs)
        if 0 <= index < len(cfgs):
            cfgs.pop(index)
            self.state.chart_configs = cfgs
            self._rebuild_charts()

    def _on_selection_change(self, *events) -> None:
        """Rebuild all charts when selection changes."""
        self._rebuild_charts()

    def _rebuild_charts(self) -> None:
        """Rebuild all chart panes from current configs and selection."""
        panes = []
        for i, cfg in enumerate(self.state.chart_configs):
            fig = self._build_chart_figure(cfg)
            if fig is None:
                continue

            plotly_pane = pn.pane.Plotly(fig, sizing_mode="stretch_width", height=280)

            idx = i
            remove_btn = pn.widgets.Button(
                name="Remove", width=70, button_type="danger",
            )
            remove_btn.on_click(lambda e, idx=idx: self._on_remove_chart(idx))

            card = pn.Card(
                plotly_pane,
                pn.Row(remove_btn, align="end"),
                title=f"{cfg['type'].title()}: {cfg['column']}",
                sizing_mode="stretch_width",
                width=400,
                collapsed=False,
            )
            panes.append(card)

        self._charts_container.objects = panes

    def _build_chart_figure(self, cfg: dict):
        """Build a Plotly figure from a chart config dict."""
        chart_type = cfg["type"]
        column = cfg["column"]
        selected_ids = self.state.selected_col_ids or None

        values = self._get_values(column)
        if values is None:
            return None

        if chart_type == "box":
            return plotly_charts.build_box(values, selected_ids, name=column)
        elif chart_type == "violin":
            return plotly_charts.build_violin(values, selected_ids, name=column)
        elif chart_type == "bar":
            return plotly_charts.build_bar(values, selected_ids, name=column)
        elif chart_type == "histogram":
            return plotly_charts.build_histogram(values, selected_ids, name=column)
        elif chart_type == "scatter":
            y_column = cfg.get("y_column", column)
            y_values = self._get_values(y_column)
            if y_values is None:
                return None
            return plotly_charts.build_scatter(
                values, y_values, selected_ids,
                x_name=column, y_name=y_column,
            )
        return None

    def _get_values(self, column: str) -> pd.Series | None:
        """Get a Series of values for the given column name.

        Checks expression matrix rows first, then col_metadata columns.
        """
        s = self.state

        # Check expression matrix rows (markers)
        if s.data is not None and column in s.data.index:
            return s.data.loc[column]

        # Check col metadata
        if s.col_metadata is not None and column in s.col_metadata.columns:
            return s.col_metadata[column]

        return None

    def build_panel(self) -> pn.Column:
        """Build the complete chart panel."""
        add_bar = pn.Row(
            self.chart_type_select,
            self.chart_column_select,
            self.chart_y_column_select,
            self.chart_add_button,
            sizing_mode="stretch_width",
            margin=(5, 0),
        )
        return pn.Column(
            add_bar,
            self._charts_container,
            sizing_mode="stretch_width",
        )
