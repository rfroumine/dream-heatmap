"""SplitEngine: partition IDs by metadata columns."""

from __future__ import annotations

from collections import OrderedDict

from ..core.metadata import MetadataFrame


class SplitEngine:
    """Partitions IDs into groups based on metadata column values.

    Produces an ordered {group_name: [ids]} dict suitable for
    IDMapper.apply_splits(). Group order follows the first-seen
    order of category values in the metadata.

    Supports splitting by one or more metadata columns. When multiple
    columns are given, groups are formed from their cross-product
    (e.g., split by ["cell_type", "batch"] → "T-cell|batch1", etc.).
    """

    @staticmethod
    def split(
        metadata: MetadataFrame,
        by: str | list[str],
    ) -> dict[str, list]:
        """Partition IDs by one or more metadata columns.

        Parameters
        ----------
        metadata : MetadataFrame
            Validated metadata aligned with matrix IDs.
        by : str or list[str]
            Column name(s) to split by.

        Returns
        -------
        dict[str, list]
            Ordered mapping of {group_name: [ids]}, preserving the
            order IDs appear in the metadata index.
        """
        if isinstance(by, str):
            by = [by]

        for col in by:
            if col not in metadata.columns:
                raise KeyError(
                    f"Split column '{col}' not found in metadata. "
                    f"Available: {metadata.columns}"
                )

        df = metadata.df
        groups: OrderedDict[str, list] = OrderedDict()

        for idx in df.index:
            # Build group key from column values
            parts = [str(df.at[idx, col]) for col in by]
            key = "|".join(parts) if len(parts) > 1 else parts[0]
            if key not in groups:
                groups[key] = []
            groups[key].append(idx)

        return dict(groups)

    @staticmethod
    def split_by_assignments(
        assignments: dict[str, list],
        all_ids: set,
    ) -> dict[str, list]:
        """Validate and return explicit user-provided assignments.

        Parameters
        ----------
        assignments : dict[str, list]
            User-provided {group_name: [ids]} mapping.
        all_ids : set
            Complete set of IDs that must be covered.

        Returns
        -------
        dict[str, list]
            The validated assignments dict.
        """
        assigned = []
        for ids in assignments.values():
            assigned.extend(ids)
        assigned_set = set(assigned)

        if len(assigned) != len(assigned_set):
            seen = set()
            dupes = []
            for x in assigned:
                if x in seen:
                    dupes.append(x)
                seen.add(x)
            raise ValueError(
                f"IDs appear in multiple groups: {dupes[:5]}"
            )

        missing = all_ids - assigned_set
        if missing:
            raise ValueError(
                f"IDs not assigned to any group: {sorted(list(missing))[:5]}"
            )

        extra = assigned_set - all_ids
        if extra:
            raise ValueError(
                f"Unknown IDs in assignments: {sorted(list(extra))[:5]}"
            )

        return assignments
