"""Dendrogram layout: convert cluster nodes to pixel coordinates."""

from __future__ import annotations

from dataclasses import dataclass

from ..transform.cluster import DendrogramNode, ClusterResult
from .cell_layout import CellLayout


@dataclass(frozen=True)
class DendrogramLink:
    """A single U-shaped link in the dendrogram, in pixel coordinates.

    Each link has three segments forming a U-shape:
    - Vertical from (x_left, y_left_child) to (x_left, y_merge)
    - Horizontal from (x_left, y_merge) to (x_right, y_merge)
    - Vertical from (x_right, y_merge) to (x_right, y_right_child)

    For row dendrograms, x is the height axis and y is the leaf axis.
    For col dendrograms, x is the leaf axis and y is the height axis.
    """

    # Leaf-axis positions (pixel)
    leaf_left: float
    leaf_right: float
    # Height-axis positions (pixel)
    height_merge: float
    height_left_child: float
    height_right_child: float
    # Member IDs for click-to-select
    member_ids: tuple

    def to_dict(self) -> dict:
        return {
            "leafLeft": self.leaf_left,
            "leafRight": self.leaf_right,
            "heightMerge": self.height_merge,
            "heightLeftChild": self.height_left_child,
            "heightRightChild": self.height_right_child,
            "memberIds": list(self.member_ids),
        }


@dataclass(frozen=True)
class DendrogramSpec:
    """Complete dendrogram rendering specification."""

    links: tuple[DendrogramLink, ...]
    # Which side: "left", "right", "top", "bottom"
    side: str
    # Pixel region for the dendrogram
    offset: float   # start of the dendrogram area on the height axis
    extent: float   # total size of the dendrogram on the height axis

    def to_dict(self) -> dict:
        return {
            "links": [link.to_dict() for link in self.links],
            "side": self.side,
            "offset": self.offset,
            "extent": self.extent,
        }


DEFAULT_DENDRO_HEIGHT = 80.0  # pixels for dendrogram area


class DendrogramLayout:
    """Converts ClusterResult dendrogram nodes to pixel coordinates.

    The leaf axis uses cell center positions from CellLayout.
    The height axis maps linkage distances to a fixed pixel range.
    """

    @staticmethod
    def compute(
        cluster_result: ClusterResult,
        cell_layout: CellLayout,
        side: str = "left",
        dendro_height: float = DEFAULT_DENDRO_HEIGHT,
        group_offset: int = 0,
    ) -> DendrogramSpec | None:
        """Compute pixel coordinates for a dendrogram.

        Parameters
        ----------
        cluster_result : ClusterResult
            From ClusterEngine.cluster().
        cell_layout : CellLayout
            Cell positions on the leaf axis.
        side : str
            "left" or "top" — determines axis orientation.
        dendro_height : float
            Pixel extent for the dendrogram.
        group_offset : int
            Visual index offset for this group within the full axis.

        Returns None if there are fewer than 2 items (no dendrogram).
        """
        nodes = cluster_result.dendrogram_nodes
        if not nodes:
            return None

        # Find max height for scaling
        max_height = max(n.height for n in nodes) if nodes else 1.0
        if max_height == 0:
            max_height = 1.0

        links: list[DendrogramLink] = []
        for node in nodes:
            # Map leaf positions to pixel centers
            leaf_left = DendrogramLayout._leaf_to_pixel(
                node.left, cell_layout, group_offset
            )
            leaf_right = DendrogramLayout._leaf_to_pixel(
                node.right, cell_layout, group_offset
            )

            # Map heights to pixel positions
            height_merge = (node.height / max_height) * dendro_height
            height_left = (node.left_height / max_height) * dendro_height
            height_right = (node.right_height / max_height) * dendro_height

            links.append(DendrogramLink(
                leaf_left=leaf_left,
                leaf_right=leaf_right,
                height_merge=height_merge,
                height_left_child=height_left,
                height_right_child=height_right,
                member_ids=node.member_ids,
            ))

        return DendrogramSpec(
            links=tuple(links),
            side=side,
            offset=0.0,
            extent=dendro_height,
        )

    @staticmethod
    def _leaf_to_pixel(
        leaf_pos: float,
        cell_layout: CellLayout,
        group_offset: int,
    ) -> float:
        """Convert a leaf position (float index) to a pixel center."""
        # leaf_pos is a float in [0, n-1] range (center of leaves)
        idx = int(round(leaf_pos))
        idx = max(0, min(idx, cell_layout._n_cells - 1))
        actual_idx = group_offset + idx
        if actual_idx < len(cell_layout.positions):
            return cell_layout.positions[actual_idx] + cell_layout.cell_size / 2
        # Fallback for edge cases
        return cell_layout.positions[-1] + cell_layout.cell_size / 2
