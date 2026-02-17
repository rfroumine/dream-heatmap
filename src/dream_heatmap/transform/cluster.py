"""ClusterEngine: hierarchical clustering via scipy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DendrogramNode:
    """A single branch/merge in the dendrogram tree.

    Coordinates are in "dendrogram space" (leaf-index units on the
    leaf axis, linkage distance on the merge axis). The layout engine
    converts these to pixel coordinates.
    """

    # The two child positions on the leaf axis
    left: float
    right: float
    # The merge height (distance)
    height: float
    # The heights of the two children (0 for leaves)
    left_height: float
    right_height: float
    # Original IDs in this subtree (for click-to-select)
    member_ids: tuple


@dataclass(frozen=True)
class ClusterResult:
    """Result of clustering a set of IDs."""

    leaf_order: np.ndarray       # IDs in clustered order
    linkage_matrix: np.ndarray   # scipy linkage matrix (n-1, 4)
    dendrogram_nodes: tuple[DendrogramNode, ...]  # for rendering
    ids: np.ndarray              # original IDs (in input order)


class ClusterEngine:
    """Hierarchical clustering with deterministic ordering.

    Wraps scipy.cluster.hierarchy to produce:
    1. A leaf ordering for reordering the IDMapper
    2. Dendrogram node data for rendering
    """

    VALID_METHODS = {
        "single", "complete", "average", "weighted",
        "centroid", "median", "ward",
    }
    VALID_METRICS = {
        "euclidean", "correlation", "cosine", "cityblock",
        "chebyshev", "braycurtis", "canberra",
    }

    @classmethod
    def cluster(
        cls,
        data: np.ndarray,
        ids: np.ndarray,
        method: str = "average",
        metric: str = "euclidean",
        optimal_ordering: bool = True,
    ) -> ClusterResult:
        """Perform hierarchical clustering.

        Parameters
        ----------
        data : (n, m) float64 array
            Data matrix. Rows are the items to cluster.
        ids : (n,) array
            IDs corresponding to each row of data.
        method : str
            Linkage method (scipy names).
        metric : str
            Distance metric.
        optimal_ordering : bool
            If True, use scipy's optimal_ordering for deterministic,
            visually clean leaf order.

        Returns
        -------
        ClusterResult
        """
        if method not in cls.VALID_METHODS:
            raise ValueError(
                f"Unknown linkage method '{method}'. "
                f"Valid: {sorted(cls.VALID_METHODS)}"
            )
        if metric not in cls.VALID_METRICS:
            raise ValueError(
                f"Unknown distance metric '{metric}'. "
                f"Valid: {sorted(cls.VALID_METRICS)}"
            )
        n = data.shape[0]
        if n < 2:
            # Single item — no clustering needed
            return ClusterResult(
                leaf_order=ids.copy(),
                linkage_matrix=np.empty((0, 4)),
                dendrogram_nodes=(),
                ids=ids.copy(),
            )

        # Handle NaN: replace with row mean for distance computation
        clean_data = cls._handle_nan(data)

        # Lazy import scipy (heavy, ~1-2s cold start)
        from scipy.cluster.hierarchy import linkage, leaves_list
        from scipy.spatial.distance import pdist

        # Compute distances and linkage
        if metric == "correlation" and method == "ward":
            # Ward requires euclidean; fall back silently
            dist = pdist(clean_data, metric="euclidean")
        else:
            dist = pdist(clean_data, metric=metric)

        Z = linkage(dist, method=method, optimal_ordering=optimal_ordering)

        # Get leaf order
        leaf_indices = leaves_list(Z)
        leaf_order = ids[leaf_indices]

        # Build dendrogram nodes for rendering
        nodes = cls._build_dendrogram_nodes(Z, ids, leaf_indices)

        return ClusterResult(
            leaf_order=leaf_order,
            linkage_matrix=Z,
            dendrogram_nodes=tuple(nodes),
            ids=ids.copy(),
        )

    @staticmethod
    def _handle_nan(data: np.ndarray) -> np.ndarray:
        """Replace NaN values with row means for distance computation."""
        if not np.any(np.isnan(data)):
            return data
        clean = data.copy()
        for i in range(clean.shape[0]):
            row = clean[i]
            mask = np.isnan(row)
            if np.all(mask):
                clean[i] = 0.0
            elif np.any(mask):
                clean[i, mask] = np.nanmean(row)
        return clean

    @staticmethod
    def _build_dendrogram_nodes(
        Z: np.ndarray,
        ids: np.ndarray,
        leaf_indices: np.ndarray,
    ) -> list[DendrogramNode]:
        """Convert scipy linkage matrix into DendrogramNode list.

        Uses scipy's dendrogram() to get the icoord/dcoord coordinates,
        then maps back to original IDs for subtree membership.
        """
        n = len(ids)
        if n < 2:
            return []

        # Build leaf position mapping: leaf_indices[i] is the original
        # index at visual position i
        leaf_pos = {int(leaf_indices[i]): i for i in range(n)}

        # Track which original indices belong to each cluster node
        # Nodes 0..n-1 are leaves, n..2n-2 are internal
        members: dict[int, list[int]] = {}
        for i in range(n):
            members[i] = [i]

        nodes = []
        for i in range(len(Z)):
            left_idx = int(Z[i, 0])
            right_idx = int(Z[i, 1])
            height = float(Z[i, 2])
            cluster_id = n + i

            left_members = members[left_idx]
            right_members = members[right_idx]
            all_members = left_members + right_members
            members[cluster_id] = all_members

            # Compute positions on leaf axis as mean of member positions
            left_positions = [leaf_pos[m] for m in left_members]
            right_positions = [leaf_pos[m] for m in right_members]
            left_center = sum(left_positions) / len(left_positions)
            right_center = sum(right_positions) / len(right_positions)

            # Child heights
            left_height = float(Z[int(Z[i, 0]) - n, 2]) if left_idx >= n else 0.0
            right_height = float(Z[int(Z[i, 1]) - n, 2]) if right_idx >= n else 0.0

            # Map member indices to original IDs
            member_ids = tuple(ids[m] for m in all_members)

            nodes.append(DendrogramNode(
                left=left_center,
                right=right_center,
                height=height,
                left_height=left_height,
                right_height=right_height,
                member_ids=member_ids,
            ))

        return nodes
