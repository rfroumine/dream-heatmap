"""Chart builder functions for the dashboard Plotly chart panel."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go


# Color constants
COLOR_ALL = "rgba(180, 180, 180, 0.5)"
COLOR_SELECTED = "rgba(31, 119, 180, 0.7)"
COLOR_ALL_LINE = "rgba(140, 140, 140, 0.8)"
COLOR_SELECTED_LINE = "rgba(31, 119, 180, 1.0)"

_LAYOUT_DEFAULTS = dict(
    template="plotly_white",
    margin=dict(l=50, r=20, t=30, b=40),
    height=250,
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", size=11),
    showlegend=True,
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="right", x=1, font=dict(size=10),
    ),
)

_COMPACT_OVERRIDES = dict(
    margin=dict(l=40, r=10, t=24, b=24),
    height=200,
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", size=10),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="right", x=1, font=dict(size=9),
    ),
)


def _get_layout(compact: bool = False, **extra) -> dict:
    """Return layout kwargs, applying compact overrides if needed."""
    layout = {**_LAYOUT_DEFAULTS, **extra}
    if compact:
        layout.update(_COMPACT_OVERRIDES)
        # Hide x-axis title in compact mode
        layout["xaxis_title"] = None
    return layout


def build_box(
    values: pd.Series,
    selected_ids: list | None = None,
    name: str = "",
    compact: bool = False,
) -> go.Figure:
    """Build a box plot with All vs Selected traces."""
    fig = go.Figure()

    fig.add_trace(go.Box(
        y=values.values, name="All",
        marker_color=COLOR_ALL, line_color=COLOR_ALL_LINE,
        boxmean="sd",
    ))

    if selected_ids:
        sel_mask = values.index.isin(selected_ids)
        sel_values = values[sel_mask]
        if len(sel_values) > 0:
            fig.add_trace(go.Box(
                y=sel_values.values, name="Selected",
                marker_color=COLOR_SELECTED, line_color=COLOR_SELECTED_LINE,
                boxmean="sd",
            ))

    fig.update_layout(**_get_layout(compact, title=name, yaxis_title=name))
    return fig


def build_violin(
    values: pd.Series,
    selected_ids: list | None = None,
    name: str = "",
    compact: bool = False,
) -> go.Figure:
    """Build a violin plot with All vs Selected traces."""
    fig = go.Figure()

    fig.add_trace(go.Violin(
        y=values.values, name="All",
        fillcolor=COLOR_ALL, line_color=COLOR_ALL_LINE,
        meanline_visible=True,
    ))

    if selected_ids:
        sel_mask = values.index.isin(selected_ids)
        sel_values = values[sel_mask]
        if len(sel_values) > 0:
            fig.add_trace(go.Violin(
                y=sel_values.values, name="Selected",
                fillcolor=COLOR_SELECTED, line_color=COLOR_SELECTED_LINE,
                meanline_visible=True,
            ))

    fig.update_layout(**_get_layout(compact, title=name, yaxis_title=name))
    return fig


def build_bar(
    values: pd.Series,
    selected_ids: list | None = None,
    name: str = "",
    compact: bool = False,
) -> go.Figure:
    """Build a bar chart showing value counts (categorical data)."""
    fig = go.Figure()

    all_counts = values.value_counts().sort_index()
    fig.add_trace(go.Bar(
        x=all_counts.index.astype(str).tolist(),
        y=all_counts.values,
        name="All",
        marker_color=COLOR_ALL,
        marker_line_color=COLOR_ALL_LINE,
        marker_line_width=1,
    ))

    if selected_ids:
        sel_mask = values.index.isin(selected_ids)
        sel_values = values[sel_mask]
        if len(sel_values) > 0:
            sel_counts = sel_values.value_counts().reindex(all_counts.index, fill_value=0)
            fig.add_trace(go.Bar(
                x=sel_counts.index.astype(str).tolist(),
                y=sel_counts.values,
                name="Selected",
                marker_color=COLOR_SELECTED,
                marker_line_color=COLOR_SELECTED_LINE,
                marker_line_width=1,
            ))

    fig.update_layout(**_get_layout(
        compact, title=name, xaxis_title=name, yaxis_title="Count", barmode="group",
    ))
    return fig


def build_scatter(
    x_values: pd.Series,
    y_values: pd.Series,
    selected_ids: list | None = None,
    x_name: str = "",
    y_name: str = "",
    compact: bool = False,
) -> go.Figure:
    """Build a scatter plot with All vs Selected points."""
    fig = go.Figure()

    fig.add_trace(go.Scattergl(
        x=x_values.values, y=y_values.values,
        mode="markers", name="All",
        marker=dict(color=COLOR_ALL, size=4, line=dict(width=0.5, color=COLOR_ALL_LINE)),
    ))

    if selected_ids:
        sel_mask = x_values.index.isin(selected_ids)
        if sel_mask.any():
            fig.add_trace(go.Scattergl(
                x=x_values[sel_mask].values, y=y_values[sel_mask].values,
                mode="markers", name="Selected",
                marker=dict(color=COLOR_SELECTED, size=5,
                            line=dict(width=0.5, color=COLOR_SELECTED_LINE)),
            ))

    fig.update_layout(**_get_layout(
        compact,
        title=f"{y_name} vs {x_name}",
        xaxis_title=x_name, yaxis_title=y_name,
    ))
    return fig


def build_histogram(
    values: pd.Series,
    selected_ids: list | None = None,
    name: str = "",
    compact: bool = False,
) -> go.Figure:
    """Build a histogram with All vs Selected traces."""
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=values.values, name="All",
        marker_color=COLOR_ALL,
        marker_line_color=COLOR_ALL_LINE,
        marker_line_width=1,
        opacity=0.7,
    ))

    if selected_ids:
        sel_mask = values.index.isin(selected_ids)
        sel_values = values[sel_mask]
        if len(sel_values) > 0:
            fig.add_trace(go.Histogram(
                x=sel_values.values, name="Selected",
                marker_color=COLOR_SELECTED,
                marker_line_color=COLOR_SELECTED_LINE,
                marker_line_width=1,
                opacity=0.7,
            ))

    fig.update_layout(**_get_layout(
        compact, title=name, xaxis_title=name, yaxis_title="Count", barmode="overlay",
    ))
    return fig
