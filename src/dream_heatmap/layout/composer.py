"""LayoutComposer: assembles all components into a final layout specification."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.id_mapper import IDMapper
from .geometry import Rect
from .cell_layout import CellLayout


# Default sizes
DEFAULT_CELL_SIZE = 12.0
DEFAULT_GAP_SIZE = 6.0
DEFAULT_PADDING = 40.0  # space for labels on each side
DEFAULT_DENDRO_HEIGHT = 80.0
MIN_CELL_SIZE = 1.0
MAX_CELL_SIZE = 50.0
TARGET_HEATMAP_WIDTH = 500.0
TARGET_HEATMAP_HEIGHT = 400.0


@dataclass
class LayoutSpec:
    """Complete layout specification sent to JS for rendering."""

    # Heatmap grid
    heatmap_rect: Rect
    row_cell_layout: CellLayout
    col_cell_layout: CellLayout

    # Overall dimensions
    total_width: float
    total_height: float

    # Matrix dimensions
    n_rows: int
    n_cols: int

    # Dendrogram space
    row_dendro_width: float = 0.0
    col_dendro_height: float = 0.0

    # Color bar rendered in legend panel (flag only, no separate rect)
    has_color_bar: bool = True

    # Annotation edge sizes (so JS can offset labels past annotations)
    right_annotation_width: float = 0.0
    bottom_annotation_height: float = 0.0

    # Legend panel
    legend_panel_rect: Rect | None = None

    def to_dict(self) -> dict:
        """Serialize to a dict for JSON transfer to JS."""
        d = {
            "heatmap": self.heatmap_rect.to_dict(),
            "rowPositions": self.row_cell_layout.to_list(),
            "colPositions": self.col_cell_layout.to_list(),
            "rowCellSize": self.row_cell_layout.cell_size,
            "colCellSize": self.col_cell_layout.cell_size,
            "totalWidth": self.total_width,
            "totalHeight": self.total_height,
            "nRows": self.n_rows,
            "nCols": self.n_cols,
            "rowDendroWidth": self.row_dendro_width,
            "colDendroHeight": self.col_dendro_height,
            "hasColorBar": self.has_color_bar,
            "rightAnnotationWidth": self.right_annotation_width,
            "bottomAnnotationHeight": self.bottom_annotation_height,
        }
        if self.legend_panel_rect is not None:
            d["legendPanel"] = self.legend_panel_rect.to_dict()
        return d


class LayoutComposer:
    """Computes the full layout for a heatmap.

    Accounts for dendrograms (left/top), annotations, and labels.
    """

    def __init__(
        self,
        cell_size: float = DEFAULT_CELL_SIZE,
        gap_size: float = DEFAULT_GAP_SIZE,
        padding: float = DEFAULT_PADDING,
        dendro_height: float = DEFAULT_DENDRO_HEIGHT,
    ) -> None:
        self._cell_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, cell_size))
        self._gap_size = gap_size
        self._padding = padding
        self._dendro_height = dendro_height

    def compute(
        self,
        row_mapper: IDMapper,
        col_mapper: IDMapper,
        has_row_dendro: bool = False,
        has_col_dendro: bool = False,
        left_annotation_width: float = 0.0,
        right_annotation_width: float = 0.0,
        top_annotation_height: float = 0.0,
        bottom_annotation_height: float = 0.0,
        legend_panel_width: float = 0.0,
        legend_panel_height: float = 0.0,
        row_label_width: float = 0.0,
        col_label_height: float = 0.0,
    ) -> LayoutSpec:
        """Compute the layout for the given row/col ID mappers."""
        row_dendro_w = self._dendro_height if has_row_dendro else 0.0
        col_dendro_h = self._dendro_height if has_col_dendro else 0.0

        # Auto-scale cell size for small matrices to target reasonable heatmap dimensions
        n_rows = row_mapper.size
        n_cols = col_mapper.size
        if n_rows > 0 and n_cols > 0:
            auto_w = TARGET_HEATMAP_WIDTH / n_cols
            auto_h = TARGET_HEATMAP_HEIGHT / n_rows
            auto_cell = min(auto_w, auto_h)
            cell_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, max(self._cell_size, auto_cell)))
        else:
            cell_size = self._cell_size

        # Heatmap origin shifts right/down for dendrograms + left/top annotations
        heatmap_x = self._padding + row_dendro_w + left_annotation_width
        heatmap_y = self._padding + col_dendro_h + top_annotation_height

        row_layout = CellLayout(
            n_cells=row_mapper.size,
            cell_size=cell_size,
            gap_positions=row_mapper.gap_positions,
            gap_size=self._gap_size,
            offset=heatmap_y,
        )
        col_layout = CellLayout(
            n_cells=col_mapper.size,
            cell_size=cell_size,
            gap_positions=col_mapper.gap_positions,
            gap_size=self._gap_size,
            offset=heatmap_x,
        )

        heatmap_rect = Rect(
            x=heatmap_x,
            y=heatmap_y,
            width=col_layout.total_size,
            height=row_layout.total_size,
        )

        # No right-side color bar — color bar is now in the legend panel below
        legend_panel_rect = None

        total_width = heatmap_x + col_layout.total_size + right_annotation_width + row_label_width + self._padding

        # Total height accounts for col labels and legend panel below heatmap
        heatmap_bottom = heatmap_y + row_layout.total_size + bottom_annotation_height + col_label_height

        # Legend panel below the heatmap area
        if legend_panel_height > 0 and legend_panel_width > 0:
            legend_gap = 16.0
            lp_x = heatmap_x
            lp_y = heatmap_bottom + legend_gap
            legend_panel_rect = Rect(
                x=lp_x, y=lp_y,
                width=legend_panel_width,
                height=legend_panel_height,
            )

        legend_bottom = 0.0
        if legend_panel_rect is not None:
            legend_bottom = legend_panel_rect.y + legend_panel_rect.height
        total_height = max(heatmap_bottom, legend_bottom) + self._padding

        return LayoutSpec(
            heatmap_rect=heatmap_rect,
            row_cell_layout=row_layout,
            col_cell_layout=col_layout,
            total_width=total_width,
            total_height=total_height,
            n_rows=row_mapper.size,
            n_cols=col_mapper.size,
            row_dendro_width=row_dendro_w,
            col_dendro_height=col_dendro_h,
            has_color_bar=True,
            right_annotation_width=right_annotation_width,
            bottom_annotation_height=bottom_annotation_height,
            legend_panel_rect=legend_panel_rect,
        )
