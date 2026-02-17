"""TransformPipeline: orchestrates split → cluster → reorder transforms."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.id_mapper import IDMapper
from ..core.metadata import MetadataFrame
from .splitter import SplitEngine
from .cluster import ClusterEngine, ClusterResult
from .reorder import ReorderEngine


@dataclass
class TransformResult:
    """Output of the full transform pipeline for one axis."""

    mapper: IDMapper
    cluster_results: dict[str, ClusterResult] | None


class TransformPipeline:
    """Orchestrates the split → cluster → reorder chain for one axis.

    Applies transforms in the correct order:
    1. Split (partition into groups)
    2. Cluster (hierarchical clustering within each group)
    3. Reorder (metadata sort within each group — only if not clustered)

    Clustering and reorder are mutually exclusive: if both are requested,
    clustering takes priority (its leaf order defines the final arrangement).
    """

    @staticmethod
    def run(
        mapper: IDMapper,
        matrix_values: np.ndarray,
        row_ids: np.ndarray,
        col_ids: np.ndarray,
        axis: str,
        *,
        # Split params
        split_metadata: MetadataFrame | None = None,
        split_by: str | list[str] | None = None,
        split_assignments: dict[str, list] | None = None,
        # Cluster params
        cluster: bool = False,
        cluster_method: str = "average",
        cluster_metric: str = "euclidean",
        cluster_optimal_ordering: bool = True,
        # Reorder params
        reorder_metadata: MetadataFrame | None = None,
        reorder_by: str | list[str] | None = None,
        reorder_ascending: bool | list[bool] = True,
    ) -> TransformResult:
        """Run the full transform pipeline for one axis.

        Parameters
        ----------
        mapper : IDMapper
            Starting mapper for this axis.
        matrix_values : ndarray
            Full matrix values.
        row_ids, col_ids : ndarray
            Matrix row/col IDs.
        axis : "row" or "col"
        split_metadata : MetadataFrame, optional
            Metadata for split-by-column.
        split_by : str or list[str], optional
            Column(s) to split by.
        split_assignments : dict, optional
            Explicit split assignments.
        cluster : bool
            Whether to cluster.
        cluster_method, cluster_metric, cluster_optimal_ordering
            Clustering parameters.
        reorder_metadata : MetadataFrame, optional
            Metadata for reorder-by-column.
        reorder_by : str or list[str], optional
            Column(s) to reorder by.
        reorder_ascending : bool or list[bool]
            Sort direction(s).

        Returns
        -------
        TransformResult with final mapper and optional cluster results.
        """
        # --- Step 1: Split ---
        if split_by is not None or split_assignments is not None:
            if split_by is not None:
                if split_metadata is None:
                    raise ValueError(
                        f"Cannot split {axis}s by metadata — no metadata provided."
                    )
                assignments = SplitEngine.split(split_metadata, split_by)
            else:
                assignments = SplitEngine.split_by_assignments(
                    split_assignments, mapper.original_ids
                )
            mapper = mapper.apply_splits(assignments)

        # --- Step 2: Cluster (takes priority over reorder) ---
        cluster_results: dict[str, ClusterResult] | None = None
        if cluster:
            cluster_results = {}
            group_orders: dict[str, np.ndarray] = {}

            for group in mapper.groups:
                group_ids = group.ids
                if len(group_ids) < 2:
                    cluster_results[group.name] = ClusterResult(
                        leaf_order=group_ids.copy(),
                        linkage_matrix=np.empty((0, 4)),
                        dendrogram_nodes=(),
                        ids=group_ids.copy(),
                    )
                    continue

                # Extract submatrix
                if axis == "row":
                    id_to_idx = {rid: i for i, rid in enumerate(row_ids)}
                    indices = [id_to_idx[gid] for gid in group_ids]
                    sub_matrix = matrix_values[indices, :]
                else:
                    id_to_idx = {cid: i for i, cid in enumerate(col_ids)}
                    indices = [id_to_idx[gid] for gid in group_ids]
                    sub_matrix = matrix_values[:, indices].T

                result = ClusterEngine.cluster(
                    data=sub_matrix,
                    ids=group_ids,
                    method=cluster_method,
                    metric=cluster_metric,
                    optimal_ordering=cluster_optimal_ordering,
                )
                cluster_results[group.name] = result
                group_orders[group.name] = result.leaf_order

            mapper = mapper.apply_reorder_within_groups(group_orders)

        # --- Step 3: Reorder (only if not clustered) ---
        elif reorder_by is not None:
            if reorder_metadata is None:
                raise ValueError(
                    f"Cannot reorder {axis}s by metadata — no metadata provided."
                )
            group_orders = {}
            for group in mapper.groups:
                sorted_ids = ReorderEngine.compute_order(
                    ids=group.ids,
                    metadata=reorder_metadata,
                    by=reorder_by,
                    ascending=reorder_ascending,
                )
                group_orders[group.name] = sorted_ids
            mapper = mapper.apply_reorder_within_groups(group_orders)

        return TransformResult(
            mapper=mapper,
            cluster_results=cluster_results,
        )
