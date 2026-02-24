"""Heatmap: the main user-facing API (builder pattern)."""

from __future__ import annotations

from typing import Callable, Any
import math

import numpy as np
import pandas as pd

from .core.matrix import MatrixData
from .core.metadata import MetadataFrame
from .core.color_scale import ColorScale
from .core.id_mapper import IDMapper
from .transform.splitter import SplitEngine
from .transform.cluster import ClusterEngine, ClusterResult
from .transform.reorder import ReorderEngine
from .layout.composer import LayoutComposer, LayoutSpec
from .layout.dendrogram_layout import DendrogramLayout, DendrogramSpec
from .layout.annotation_layout import AnnotationLayoutEngine, MAX_TRACKS_PER_EDGE
from .layout.label_layout import LabelLayoutEngine
from .annotation.base import AnnotationTrack, VALID_EDGES
from .annotation.categorical import CategoricalAnnotation
from .widget.selection import SelectionState


class Heatmap:
    """Interactive heatmap builder.

    Usage::

        import dream_heatmap as dh

        hm = dh.Heatmap(matrix_df)
        hm.set_colormap("viridis", vmin=0, vmax=100)
        hm.cluster_rows(metric="correlation", method="ward")
        hm.show()

        # Access selection
        print(hm.selection)
        hm.on_select(lambda rows, cols: print(rows, cols))
    """

    PRIMARY_GAP_PX = 8.0
    SECONDARY_GAP_PX = 3.0

    def __init__(self, data: pd.DataFrame) -> None:
        self._matrix = MatrixData(data)
        self._row_metadata: MetadataFrame | None = None
        self._col_metadata: MetadataFrame | None = None

        # Color scale — defaults computed from data range
        vmin, vmax = self._matrix.finite_range()
        self._color_scale = ColorScale("viridis", vmin=vmin, vmax=vmax)

        # ID mappers — initial (no splits, no clustering)
        self._row_mapper = IDMapper.from_ids(self._matrix.row_ids)
        self._col_mapper = IDMapper.from_ids(self._matrix.col_ids)

        # Clustering results
        self._row_cluster: dict[str, ClusterResult] | None = None
        self._col_cluster: dict[str, ClusterResult] | None = None
        self._row_dendro_specs: list[DendrogramSpec] | None = None
        self._col_dendro_specs: list[DendrogramSpec] | None = None

        # Annotations: {edge: [AnnotationTrack, ...]}
        self._annotations: dict[str, list[AnnotationTrack]] = {
            "left": [], "right": [], "top": [], "bottom": [],
        }

        # Label display mode
        self._row_label_mode: str = "auto"
        self._col_label_mode: str = "auto"
        self._row_label_side: str = "right"
        self._col_label_side: str = "bottom"

        # Dendrogram visibility (used by dashboard to hide dendrograms)
        self._show_row_dendro: bool = True
        self._show_col_dendro: bool = True

        # Dendrogram side: which edge to place the dendrogram on
        self._row_dendro_side: str = "left"   # "left" or "right"
        self._col_dendro_side: str = "top"    # "top" or "bottom"

        # Layout
        self._layout_composer = LayoutComposer()
        self._layout: LayoutSpec | None = None

        # Selection
        self._selection = SelectionState()

        # Color bar title
        self._color_bar_title: str | None = None

        # Plot title (rendered as SVG text above the heatmap)
        self._title: str | None = None

        # Value description (main color bar title; scaling info becomes subtitle)
        self._value_description: str | None = None

        # Per-gap sizing for hierarchical splits (set by dashboard)
        self._row_gap_sizes: dict[int, float] | None = None
        self._col_gap_sizes: dict[int, float] | None = None

        # Widget reference (created on show())
        self._widget = None

    # --- Metadata ---

    def set_row_metadata(self, df: pd.DataFrame) -> Heatmap:
        """Set row metadata. Index must match matrix row IDs exactly."""
        self._row_metadata = MetadataFrame(
            df, pd.Index(self._matrix.row_ids), axis_name="row"
        )
        return self

    def set_col_metadata(self, df: pd.DataFrame) -> Heatmap:
        """Set column metadata. Index must match matrix column IDs exactly."""
        self._col_metadata = MetadataFrame(
            df, pd.Index(self._matrix.col_ids), axis_name="col"
        )
        return self

    # --- Color ---

    def set_colormap(
        self,
        cmap: str = "viridis",
        vmin: float | None = None,
        vmax: float | None = None,
        color_bar_title: str | None = None,
    ) -> Heatmap:
        """Set the colormap and optional value range.

        Parameters
        ----------
        cmap : str
            Matplotlib colormap name.
        vmin, vmax : float, optional
            Value range for the color scale.
        color_bar_title : str, optional
            Title displayed above the color bar in the legend panel.
        """
        data_vmin, data_vmax = self._matrix.finite_range()
        self._color_scale = ColorScale(
            cmap_name=cmap,
            vmin=vmin if vmin is not None else data_vmin,
            vmax=vmax if vmax is not None else data_vmax,
        )
        self._color_bar_title = color_bar_title
        return self

    # --- Title ---

    def set_title(self, title: str) -> Heatmap:
        """Set a title displayed above the heatmap.

        Parameters
        ----------
        title : str
            Title text. Pass empty string to remove.
        """
        self._title = title if title else None
        return self

    # --- Value description ---

    def set_value_description(self, description: str) -> Heatmap:
        """Set a description for the color bar values.

        This appears as the main color bar title, while any
        auto-generated scaling label becomes a subtitle below it.

        Parameters
        ----------
        description : str
            Value description (e.g. "Expression (TPM)").
        """
        self._value_description = description if description else None
        return self

    # --- Splits ---

    def split_rows(
        self,
        by: str | list[str] | None = None,
        assignments: dict[str, list] | None = None,
    ) -> Heatmap:
        """Split rows into groups with visual gaps between them.

        Parameters
        ----------
        by : str or list[str], optional
            Metadata column name(s) to split by. Requires row metadata
            to be set via set_row_metadata().
        assignments : dict[str, list], optional
            Explicit {group_name: [row_ids]} mapping.

        Exactly one of ``by`` or ``assignments`` must be provided.
        """
        split_assignments = self._resolve_split(
            by=by,
            assignments=assignments,
            metadata=self._row_metadata,
            mapper=self._row_mapper,
            axis_name="row",
        )
        self._row_mapper = self._row_mapper.apply_splits(split_assignments)
        if isinstance(by, list) and len(by) >= 2:
            self._row_gap_sizes = self._compute_gap_sizes(self._row_mapper)
        return self

    def split_cols(
        self,
        by: str | list[str] | None = None,
        assignments: dict[str, list] | None = None,
    ) -> Heatmap:
        """Split columns into groups with visual gaps between them.

        Parameters
        ----------
        by : str or list[str], optional
            Metadata column name(s) to split by. Requires col metadata
            to be set via set_col_metadata().
        assignments : dict[str, list], optional
            Explicit {group_name: [col_ids]} mapping.

        Exactly one of ``by`` or ``assignments`` must be provided.
        """
        split_assignments = self._resolve_split(
            by=by,
            assignments=assignments,
            metadata=self._col_metadata,
            mapper=self._col_mapper,
            axis_name="col",
        )
        self._col_mapper = self._col_mapper.apply_splits(split_assignments)
        if isinstance(by, list) and len(by) >= 2:
            self._col_gap_sizes = self._compute_gap_sizes(self._col_mapper)
        return self

    # --- Clustering ---

    def cluster_rows(
        self,
        method: str = "average",
        metric: str = "euclidean",
        optimal_ordering: bool = True,
    ) -> Heatmap:
        """Cluster rows hierarchically within each split group.

        Reorders rows by leaf order and generates dendrogram data.
        If rows are split, clustering is done independently per group.
        """
        self._row_cluster, self._row_mapper = self._do_cluster(
            mapper=self._row_mapper,
            axis="row",
            method=method,
            metric=metric,
            optimal_ordering=optimal_ordering,
        )
        return self

    def cluster_cols(
        self,
        method: str = "average",
        metric: str = "euclidean",
        optimal_ordering: bool = True,
    ) -> Heatmap:
        """Cluster columns hierarchically within each split group.

        Reorders columns by leaf order and generates dendrogram data.
        If columns are split, clustering is done independently per group.
        """
        self._col_cluster, self._col_mapper = self._do_cluster(
            mapper=self._col_mapper,
            axis="col",
            method=method,
            metric=metric,
            optimal_ordering=optimal_ordering,
        )
        return self

    # --- Reorder ---

    def order_rows(
        self,
        by: str | list[str],
        ascending: bool | list[bool] = True,
    ) -> Heatmap:
        """Reorder rows within each split group by metadata column(s).

        Parameters
        ----------
        by : str or list[str]
            Metadata column name(s) to sort by. Requires row metadata
            to be set via set_row_metadata().
        ascending : bool or list[bool]
            Sort direction(s). Default True.

        Note: If rows are also clustered, clustering leaf order takes
        priority. Call order_rows OR cluster_rows, not both.
        """
        if self._row_metadata is None:
            raise ValueError(
                "Cannot reorder rows — call set_row_metadata() first."
            )
        group_orders: dict[str, np.ndarray] = {}
        for group in self._row_mapper.groups:
            sorted_ids = ReorderEngine.compute_order(
                ids=group.ids,
                metadata=self._row_metadata,
                by=by,
                ascending=ascending,
            )
            group_orders[group.name] = sorted_ids
        self._row_mapper = self._row_mapper.apply_reorder_within_groups(
            group_orders
        )
        return self

    def order_cols(
        self,
        by: str | list[str],
        ascending: bool | list[bool] = True,
    ) -> Heatmap:
        """Reorder columns within each split group by metadata column(s).

        Parameters
        ----------
        by : str or list[str]
            Metadata column name(s) to sort by. Requires col metadata
            to be set via set_col_metadata().
        ascending : bool or list[bool]
            Sort direction(s). Default True.

        Note: If columns are also clustered, clustering leaf order takes
        priority. Call order_cols OR cluster_cols, not both.
        """
        if self._col_metadata is None:
            raise ValueError(
                "Cannot reorder columns — call set_col_metadata() first."
            )
        group_orders: dict[str, np.ndarray] = {}
        for group in self._col_mapper.groups:
            sorted_ids = ReorderEngine.compute_order(
                ids=group.ids,
                metadata=self._col_metadata,
                by=by,
                ascending=ascending,
            )
            group_orders[group.name] = sorted_ids
        self._col_mapper = self._col_mapper.apply_reorder_within_groups(
            group_orders
        )
        return self

    # --- Annotations ---

    def add_annotation(
        self,
        edge: str,
        annotation: AnnotationTrack,
    ) -> Heatmap:
        """Add an annotation track to an edge of the heatmap.

        Parameters
        ----------
        edge : str
            One of 'left', 'right', 'top', 'bottom'.
        annotation : AnnotationTrack
            The annotation to add.

        Maximum 3 annotations per edge.
        """
        if edge not in VALID_EDGES:
            raise ValueError(
                f"Invalid edge '{edge}'. Must be one of: {sorted(VALID_EDGES)}"
            )
        if len(self._annotations[edge]) >= MAX_TRACKS_PER_EDGE:
            raise ValueError(
                f"Maximum {MAX_TRACKS_PER_EDGE} annotations per edge. "
                f"'{edge}' already has {len(self._annotations[edge])}."
            )
        self._annotations[edge].append(annotation)
        return self

    # --- Size ---

    def set_size(
        self,
        max_width: float | None = None,
        max_height: float | None = None,
    ) -> Heatmap:
        """Control the maximum dimensions of the rendered heatmap.

        Cell sizes are automatically adjusted to fit within these constraints.
        Row and column cell sizes are computed independently.

        Parameters
        ----------
        max_width : float, optional
            Maximum total width in pixels (default 1000).
        max_height : float, optional
            Maximum total height in pixels (default 800).
        """
        if max_width is not None:
            self._layout_composer._max_width = max_width
        if max_height is not None:
            self._layout_composer._max_height = max_height
        return self

    # --- Labels ---

    def set_label_display(
        self,
        rows: str = "auto",
        cols: str = "auto",
        row_side: str | None = None,
        col_side: str | None = None,
    ) -> Heatmap:
        """Control row/column label display.

        Parameters
        ----------
        rows : str
            'all', 'auto', or 'none'.
        cols : str
            'all', 'auto', or 'none'.
        row_side : str, optional
            'left' or 'right' (default 'right').
        col_side : str, optional
            'top' or 'bottom' (default 'bottom').
        """
        valid = {"all", "auto", "none"}
        if rows not in valid:
            raise ValueError(f"rows must be one of {valid}, got '{rows}'")
        if cols not in valid:
            raise ValueError(f"cols must be one of {valid}, got '{cols}'")
        self._row_label_mode = rows
        self._col_label_mode = cols
        if row_side is not None:
            if row_side not in ("left", "right"):
                raise ValueError(f"row_side must be 'left' or 'right', got '{row_side}'")
            self._row_label_side = row_side
        if col_side is not None:
            if col_side not in ("top", "bottom"):
                raise ValueError(f"col_side must be 'top' or 'bottom', got '{col_side}'")
            self._col_label_side = col_side
        return self

    # --- Dendrogram placement ---

    def set_dendro_side(
        self,
        row_side: str | None = None,
        col_side: str | None = None,
    ) -> Heatmap:
        """Control which edge dendrograms are placed on.

        Parameters
        ----------
        row_side : str, optional
            'left' or 'right' (default 'left').
        col_side : str, optional
            'top' or 'bottom' (default 'top').
        """
        if row_side is not None:
            if row_side not in ("left", "right"):
                raise ValueError(f"row_side must be 'left' or 'right', got '{row_side}'")
            self._row_dendro_side = row_side
        if col_side is not None:
            if col_side not in ("top", "bottom"):
                raise ValueError(f"col_side must be 'top' or 'bottom', got '{col_side}'")
            self._col_dendro_side = col_side
        return self

    # --- Concatenation ---

    @classmethod
    def hconcat(cls, *heatmaps: Heatmap) -> Any:
        """Horizontally concatenate heatmaps (shared rows, different columns).

        Returns a HeatmapList that can be shown or queried.
        """
        from .concat.heatmap_list import HeatmapList
        return HeatmapList(list(heatmaps), direction="horizontal")

    @classmethod
    def vconcat(cls, *heatmaps: Heatmap) -> Any:
        """Vertically concatenate heatmaps (shared columns, different rows).

        Returns a HeatmapList that can be shown or queried.
        """
        from .concat.heatmap_list import HeatmapList
        return HeatmapList(list(heatmaps), direction="vertical")

    # --- Display ---

    def show(self) -> Any:
        """Render the heatmap in Jupyter. Returns the widget."""
        self._compute_layout()

        from .widget.heatmap_widget import HeatmapWidget

        # Build extra config data
        dendro_data = self._build_dendrogram_data()
        annotation_data = self._build_annotation_data()
        label_data = self._build_label_data()
        legend_data = self._build_legend_data()

        # Determine color bar title/subtitle
        # If user set a value_description, it becomes the main title
        # and the auto-generated color_bar_title becomes the subtitle.
        cb_title = self._value_description or self._color_bar_title
        cb_subtitle = self._color_bar_title if self._value_description else None

        self._widget = HeatmapWidget(
            matrix=self._matrix,
            color_scale=self._color_scale,
            row_mapper=self._row_mapper,
            col_mapper=self._col_mapper,
            layout=self._layout,
            selection_state=self._selection,
            dendrograms=dendro_data,
            annotations=annotation_data,
            labels=label_data,
            legends=legend_data,
            color_bar_title=cb_title,
            color_bar_subtitle=cb_subtitle,
            title=self._title,
        )
        self._widget.set_zoom_callback(self._handle_zoom)
        return self._widget

    def to_html(self, path: str, title: str = "dream-heatmap") -> None:
        """Export the heatmap as a standalone HTML file.

        Parameters
        ----------
        path : str
            Output file path.
        title : str
            HTML page title.
        """
        self._compute_layout()
        from .export.html_export import HTMLExporter

        cb_title = self._value_description or self._color_bar_title
        cb_subtitle = self._color_bar_title if self._value_description else None

        HTMLExporter.export(
            path=path,
            matrix=self._matrix,
            color_scale=self._color_scale,
            row_mapper=self._row_mapper,
            col_mapper=self._col_mapper,
            layout=self._layout,
            title=title,
            dendrograms=self._build_dendrogram_data(),
            annotations=self._build_annotation_data(),
            labels=self._build_label_data(),
            legends=self._build_legend_data(),
            color_bar_title=cb_title,
            color_bar_subtitle=cb_subtitle,
            heatmap_title=self._title,
        )

    # --- Selection ---

    @property
    def selection(self) -> dict[str, list]:
        """Current selection: {row_ids: [...], col_ids: [...]}."""
        return self._selection.value

    def on_select(self, callback: Callable[[list, list], Any]) -> Heatmap:
        """Register a callback: fn(row_ids, col_ids) called on selection."""
        self._selection.on_select(callback)
        return self

    # --- Zoom ---

    @staticmethod
    def _remap_gap_sizes(
        gap_sizes: dict[int, float] | None, start: int, end: int,
    ) -> dict[int, float] | None:
        """Remap gap_sizes keys from original to zoomed coordinate space."""
        if gap_sizes is None:
            return None
        remapped = {
            g - start: size
            for g, size in gap_sizes.items()
            if start < g < end
        }
        return remapped if remapped else None

    def _handle_zoom(self, zoom_range: dict | None) -> None:
        """Handle zoom events from JS. Recomputes layout with zoomed mappers."""
        if self._widget is None:
            return

        if zoom_range is None:
            # Reset: use original mappers and full matrix
            zoomed_row = self._row_mapper
            zoomed_col = self._col_mapper
            zoomed_matrix = self._matrix
        elif "row_ids" in zoom_range:
            # ID-based zoom (annotation click): filter to specific IDs
            zoomed_row = self._row_mapper.apply_zoom_by_ids(zoom_range["row_ids"])
            zoomed_col = self._col_mapper.apply_zoom_by_ids(zoom_range["col_ids"])
            zoomed_matrix = self._matrix.slice(
                zoomed_row.visual_order, zoomed_col.visual_order,
            )
        else:
            zoomed_row = self._row_mapper.apply_zoom(
                zoom_range["row_start"], zoom_range["row_end"]
            )
            zoomed_col = self._col_mapper.apply_zoom(
                zoom_range["col_start"], zoom_range["col_end"]
            )
            zoomed_matrix = self._matrix.slice(
                zoomed_row.visual_order, zoomed_col.visual_order,
            )

        # Remap gap sizes for zoomed coordinate space
        if zoom_range is not None and "row_ids" not in zoom_range:
            zoomed_row_gap_sizes = Heatmap._remap_gap_sizes(
                self._row_gap_sizes,
                zoom_range["row_start"], zoom_range["row_end"],
            )
            zoomed_col_gap_sizes = Heatmap._remap_gap_sizes(
                self._col_gap_sizes,
                zoom_range["col_start"], zoom_range["col_end"],
            )
        elif zoom_range is not None:
            # ID-based zoom: no gap remapping needed
            zoomed_row_gap_sizes = None
            zoomed_col_gap_sizes = None
        else:
            zoomed_row_gap_sizes = self._row_gap_sizes
            zoomed_col_gap_sizes = self._col_gap_sizes

        # Recompute layout for zoomed view (legends persist during zoom)
        legend_w, legend_h = self._estimate_legend_dimensions()
        left_lbl_w, right_lbl_w, top_lbl_h, bottom_lbl_h = self._estimate_label_space(zoomed_row, zoomed_col)
        zoomed_layout = self._layout_composer.compute(
            zoomed_row,
            zoomed_col,
            has_row_dendro=(self._row_cluster is not None and self._show_row_dendro),
            has_col_dendro=(self._col_cluster is not None and self._show_col_dendro),
            left_annotation_width=AnnotationLayoutEngine.total_edge_width(
                self._annotations["left"]
            ),
            right_annotation_width=AnnotationLayoutEngine.total_edge_width(
                self._annotations["right"]
            ),
            top_annotation_height=AnnotationLayoutEngine.total_edge_width(
                self._annotations["top"]
            ),
            bottom_annotation_height=AnnotationLayoutEngine.total_edge_width(
                self._annotations["bottom"]
            ),
            legend_panel_width=legend_w,
            legend_panel_height=legend_h,
            left_label_width=left_lbl_w,
            right_label_width=right_lbl_w,
            top_label_height=top_lbl_h,
            bottom_label_height=bottom_lbl_h,
            row_gap_sizes=zoomed_row_gap_sizes,
            col_gap_sizes=zoomed_col_gap_sizes,
            title_height=28.0 if self._title else 0.0,
            row_dendro_side=self._row_dendro_side,
            col_dendro_side=self._col_dendro_side,
        )

        # Rebuild annotations and labels for zoomed mappers
        zoomed_annotations = self._build_annotation_data(
            row_mapper=zoomed_row, col_mapper=zoomed_col,
        )
        zoomed_labels = self._build_label_data(
            row_mapper=zoomed_row, col_mapper=zoomed_col,
            layout=zoomed_layout,
        )
        # Dendrograms are not meaningful after zoom — omit them
        zoomed_dendrograms = None if zoom_range is not None else self._build_dendrogram_data()

        cb_title = self._value_description or self._color_bar_title
        cb_subtitle = self._color_bar_title if self._value_description else None

        self._widget.update_data(
            zoomed_matrix,
            self._color_scale,
            zoomed_row,
            zoomed_col,
            zoomed_layout,
            dendrograms=zoomed_dendrograms,
            annotations=zoomed_annotations,
            labels=zoomed_labels,
            legends=self._build_legend_data(),
            color_bar_title=cb_title,
            color_bar_subtitle=cb_subtitle,
            title=self._title,
        )

    # --- Internal ---

    def _compute_gap_sizes(self, mapper: IDMapper) -> dict[int, float] | None:
        """Build {gap_position: gap_px} for hierarchical (2-level) splits.

        Primary-level boundaries (first value in "val1|val2" group name changes)
        get wider gaps; secondary boundaries get narrower gaps.
        """
        groups = mapper.groups
        if not groups:
            return None
        gap_sizes: dict[int, float] = {}
        running = 0
        prev_primary = None
        for group in groups:
            if running > 0:
                current_primary = group.name.split("|")[0]
                if current_primary != prev_primary:
                    gap_sizes[running] = self.PRIMARY_GAP_PX
                else:
                    gap_sizes[running] = self.SECONDARY_GAP_PX
            prev_primary = group.name.split("|")[0]
            running += len(group.ids)
        return gap_sizes if gap_sizes else None

    def _resolve_split(
        self,
        by: str | list[str] | None,
        assignments: dict[str, list] | None,
        metadata: MetadataFrame | None,
        mapper: IDMapper,
        axis_name: str,
    ) -> dict[str, list]:
        """Resolve split arguments into a validated assignments dict."""
        if by is not None and assignments is not None:
            raise ValueError(
                "Provide either 'by' or 'assignments', not both."
            )
        if by is None and assignments is None:
            raise ValueError(
                "Provide either 'by' (metadata column) or 'assignments' "
                "(explicit {group: [ids]} dict)."
            )
        if by is not None:
            if metadata is None:
                raise ValueError(
                    f"Cannot split {axis_name}s by metadata column — "
                    f"call set_{axis_name}_metadata() first."
                )
            return SplitEngine.split(metadata, by)
        else:
            return SplitEngine.split_by_assignments(
                assignments, mapper.original_ids
            )

    def _do_cluster(
        self,
        mapper: IDMapper,
        axis: str,
        method: str,
        metric: str,
        optimal_ordering: bool,
    ) -> tuple[dict[str, ClusterResult], IDMapper]:
        """Cluster within each group of the mapper. Returns cluster results and updated mapper."""
        matrix_values = self._matrix.values
        row_ids = self._matrix.row_ids
        col_ids = self._matrix.col_ids

        cluster_results: dict[str, ClusterResult] = {}
        group_orders: dict[str, np.ndarray] = {}

        for group in mapper.groups:
            group_ids = group.ids
            if len(group_ids) < 2:
                # Single-item group — no clustering
                cluster_results[group.name] = ClusterResult(
                    leaf_order=group_ids.copy(),
                    linkage_matrix=np.empty((0, 4)),
                    dendrogram_nodes=(),
                    ids=group_ids.copy(),
                )
                continue

            # Extract submatrix for this group
            if axis == "row":
                # Find row indices for the group IDs
                id_to_idx = {rid: i for i, rid in enumerate(row_ids)}
                indices = [id_to_idx[gid] for gid in group_ids]
                sub_matrix = matrix_values[indices, :]
            else:
                id_to_idx = {cid: i for i, cid in enumerate(col_ids)}
                indices = [id_to_idx[gid] for gid in group_ids]
                sub_matrix = matrix_values[:, indices].T  # cluster by column = transpose

            result = ClusterEngine.cluster(
                data=sub_matrix,
                ids=group_ids,
                method=method,
                metric=metric,
                optimal_ordering=optimal_ordering,
            )
            cluster_results[group.name] = result
            group_orders[group.name] = result.leaf_order

        updated_mapper = mapper.apply_reorder_within_groups(group_orders)
        return cluster_results, updated_mapper

    def _compute_layout(self) -> None:
        """Compute layout from current state."""
        legend_w, legend_h = self._estimate_legend_dimensions()
        left_lbl_w, right_lbl_w, top_lbl_h, bottom_lbl_h = self._estimate_label_space()
        self._layout = self._layout_composer.compute(
            self._row_mapper,
            self._col_mapper,
            has_row_dendro=(self._row_cluster is not None and self._show_row_dendro),
            has_col_dendro=(self._col_cluster is not None and self._show_col_dendro),
            left_annotation_width=AnnotationLayoutEngine.total_edge_width(
                self._annotations["left"]
            ),
            right_annotation_width=AnnotationLayoutEngine.total_edge_width(
                self._annotations["right"]
            ),
            top_annotation_height=AnnotationLayoutEngine.total_edge_width(
                self._annotations["top"]
            ),
            bottom_annotation_height=AnnotationLayoutEngine.total_edge_width(
                self._annotations["bottom"]
            ),
            legend_panel_width=legend_w,
            legend_panel_height=legend_h,
            left_label_width=left_lbl_w,
            right_label_width=right_lbl_w,
            top_label_height=top_lbl_h,
            bottom_label_height=bottom_lbl_h,
            row_gap_sizes=self._row_gap_sizes,
            col_gap_sizes=self._col_gap_sizes,
            title_height=28.0 if self._title else 0.0,
            row_dendro_side=self._row_dendro_side,
            col_dendro_side=self._col_dendro_side,
        )

    def _build_dendrogram_data(self) -> dict | None:
        """Build dendrogram spec dicts for JS rendering."""
        if self._row_cluster is None and self._col_cluster is None:
            return None

        result: dict = {}

        if self._row_cluster is not None and self._show_row_dendro and self._layout is not None:
            row_specs = self._build_axis_dendrograms(
                self._row_cluster, self._row_mapper,
                self._layout.row_cell_layout, self._row_dendro_side,
            )
            if row_specs:
                # Merge all group dendrograms into one spec
                all_links = []
                for spec in row_specs:
                    all_links.extend(link.to_dict() for link in spec.links)
                result["row"] = {
                    "links": all_links,
                    "side": self._row_dendro_side,
                    "offset": 0.0,
                    "extent": self._layout.row_dendro_width,
                }

        if self._col_cluster is not None and self._show_col_dendro and self._layout is not None:
            col_specs = self._build_axis_dendrograms(
                self._col_cluster, self._col_mapper,
                self._layout.col_cell_layout, self._col_dendro_side,
            )
            if col_specs:
                all_links = []
                for spec in col_specs:
                    all_links.extend(link.to_dict() for link in spec.links)
                result["col"] = {
                    "links": all_links,
                    "side": self._col_dendro_side,
                    "offset": 0.0,
                    "extent": self._layout.col_dendro_height,
                }

        return result if result else None

    def _build_axis_dendrograms(
        self,
        cluster_results: dict[str, ClusterResult],
        mapper: IDMapper,
        cell_layout,
        side: str,
    ) -> list[DendrogramSpec]:
        """Build DendrogramSpecs for all groups on one axis."""
        specs = []
        offset = 0
        for group in mapper.groups:
            if group.name in cluster_results:
                cr = cluster_results[group.name]
                if cr.dendrogram_nodes:
                    spec = DendrogramLayout.compute(
                        cluster_result=cr,
                        cell_layout=cell_layout,
                        side=side,
                        dendro_height=self._layout_composer._dendro_height,
                        group_offset=offset,
                    )
                    if spec is not None:
                        specs.append(spec)
            offset += len(group)
        return specs

    def _build_annotation_data(
        self,
        row_mapper: IDMapper | None = None,
        col_mapper: IDMapper | None = None,
    ) -> dict | None:
        """Build annotation data dicts for JS rendering."""
        has_any = any(
            tracks for tracks in self._annotations.values()
        )
        if not has_any:
            return None

        rm = row_mapper or self._row_mapper
        cm = col_mapper or self._col_mapper

        result: dict = {}
        edge_mapper = {
            "left": rm,
            "right": rm,
            "top": cm,
            "bottom": cm,
        }

        for edge, tracks in self._annotations.items():
            if not tracks:
                continue
            mapper = edge_mapper[edge]
            specs = AnnotationLayoutEngine.compute_edge_tracks(
                tracks, edge, mapper.visual_order,
            )
            result[edge] = [
                {
                    "name": spec.name,
                    "edge": spec.edge,
                    "offset": spec.offset,
                    "trackWidth": spec.track_width,
                    "renderData": spec.render_data,
                }
                for spec in specs
            ]
        return result if result else None

    def _build_label_data(
        self,
        row_mapper: IDMapper | None = None,
        col_mapper: IDMapper | None = None,
        layout: LayoutSpec | None = None,
    ) -> dict | None:
        """Build label data for JS rendering."""
        lay = layout or self._layout
        if lay is None:
            return None

        rm = row_mapper or self._row_mapper
        cm = col_mapper or self._col_mapper

        result: dict = {}
        font_size = 10.0  # Default font size

        if self._row_label_mode != "none":
            row_labels = LabelLayoutEngine.compute(
                ids=rm.visual_order,
                cell_layout=lay.row_cell_layout,
                mode=self._row_label_mode,
                font_size=font_size,
            )
            result["row"] = {
                "labels": LabelLayoutEngine.serialize(row_labels, font_size=font_size),
                "side": self._row_label_side,
            }

        if self._col_label_mode != "none":
            col_labels = LabelLayoutEngine.compute(
                ids=cm.visual_order,
                cell_layout=lay.col_cell_layout,
                mode=self._col_label_mode,
                font_size=font_size,
            )
            result["col"] = {
                "labels": LabelLayoutEngine.serialize(col_labels, font_size=font_size),
                "side": self._col_label_side,
            }

        return result if result else None

    def _build_legend_data(self) -> list[dict] | None:
        """Collect categorical annotation legends from all edges.

        Deduplicates by (name, frozenset(colorMap.items())).
        Returns a list of {name, entries: [{label, color}]} or None.
        """
        seen: set[tuple] = set()
        legends: list[dict] = []

        for edge in ("top", "bottom", "left", "right"):
            for track in self._annotations[edge]:
                if not isinstance(track, CategoricalAnnotation):
                    continue
                color_map = track.colors
                key = (track.name, frozenset(color_map.items()))
                if key in seen:
                    continue
                seen.add(key)
                legends.append({
                    "name": track.name,
                    "entries": [
                        {"label": cat, "color": color_map[cat]}
                        for cat in track.categories
                    ],
                })

        return legends if legends else None

    def _estimate_label_space(
        self,
        row_mapper: IDMapper | None = None,
        col_mapper: IDMapper | None = None,
    ) -> tuple[float, float, float, float]:
        """Estimate extra space needed for row and column labels.

        Returns (left_label_w, right_label_w, top_label_h, bottom_label_h).
        Only the relevant side gets non-zero size based on label side setting.
        """
        char_width = 6.5
        rm = row_mapper or self._row_mapper
        cm = col_mapper or self._col_mapper

        row_label_width = 0.0
        if self._row_label_mode != "none" and rm.size > 0:
            max_len = max(len(str(rid)) for rid in rm.visual_order)
            row_label_width = max_len * char_width + 10

        col_label_height = 0.0
        if self._col_label_mode != "none" and cm.size > 0:
            max_len = max(len(str(cid)) for cid in cm.visual_order)
            col_label_height = max_len * char_width * math.sin(math.radians(45)) + 10

        left_label_w = row_label_width if self._row_label_side == "left" else 0.0
        right_label_w = row_label_width if self._row_label_side == "right" else 0.0
        top_label_h = col_label_height if self._col_label_side == "top" else 0.0
        bottom_label_h = col_label_height if self._col_label_side == "bottom" else 0.0

        return left_label_w, right_label_w, top_label_h, bottom_label_h

    def _estimate_legend_dimensions(self) -> tuple[float, float]:
        """Estimate the pixel width and height needed for the legend panel.

        Uses vertical stacking: color bar on top, categorical legends stacked
        below. Returns (width, height).
        """
        # Constants matching legend_renderer.js
        swatch_size = 11.0
        swatch_label_gap = 7.0
        char_width = 6.5  # approximate at 10px font
        row_height = 16.0
        title_height = 18.0
        block_gap = 20.0  # vertical gap between stacked blocks
        MAX_VISIBLE = 10
        MAX_LEGEND_WIDTH = 300.0

        # Color bar block dimensions
        has_cb_title = bool(self._value_description or self._color_bar_title)
        has_cb_subtitle = bool(self._value_description and self._color_bar_title)
        color_bar_width = 130.0  # 120px bar + ~10px tick overhang
        color_bar_height = 26.0
        if has_cb_title:
            color_bar_height += 16.0
        if has_cb_subtitle:
            color_bar_height += 14.0

        # Build list of (width, height) blocks
        blocks: list[tuple[float, float]] = []
        blocks.append((color_bar_width, color_bar_height))

        legends = self._build_legend_data()
        if legends:
            for legend in legends:
                entries = legend["entries"]
                n = len(entries)
                title_w = len(legend["name"]) * char_width

                # Compute column layout (matches legend_renderer.js thresholds)
                if n <= 4:
                    num_cols = 1
                    rows_per_col = n
                    truncated = False
                elif n <= MAX_VISIBLE:
                    num_cols = 2
                    rows_per_col = math.ceil(n / 2)
                    truncated = False
                else:
                    num_cols = 2
                    rows_per_col = 5
                    truncated = True

                # Width: compute from actual label lengths, cap at MAX_LEGEND_WIDTH
                max_label_len = max(
                    (len(e["label"]) for e in entries), default=0,
                )
                col_content_w = swatch_size + swatch_label_gap + max_label_len * char_width
                if num_cols == 1:
                    block_w = max(title_w, col_content_w) + 10.0
                else:
                    column_gap_px = 12.0  # matches JS columnGap
                    block_w = min(col_content_w * 2 + column_gap_px + 10.0, MAX_LEGEND_WIDTH)

                block_h = title_height + rows_per_col * row_height + (14.0 if truncated else 0.0)
                blocks.append((block_w, block_h))

        # Vertical stack: width is the widest block, height is all blocks stacked
        total_width = min(max(bw for bw, bh in blocks), MAX_LEGEND_WIDTH)
        total_height = sum(bh for bw, bh in blocks) + block_gap * (len(blocks) - 1)

        return total_width, total_height
