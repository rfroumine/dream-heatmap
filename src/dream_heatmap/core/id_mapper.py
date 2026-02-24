"""IDMapper: the critical class solving the ruler problem.

Maps between original IDs, visual order, and pixel space.
Immutable — each transform returns a new IDMapper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class SplitGroup:
    """A contiguous group of IDs within a split."""

    name: str
    ids: np.ndarray  # original IDs in visual order within this group

    def __len__(self) -> int:
        return len(self.ids)


@dataclass(frozen=True)
class IDMapper:
    """Maps between original IDs and their visual positions.

    The visual_order array contains the original IDs in the exact order
    they appear on screen. gap_positions marks indices where visual gaps
    (from splits) should appear.

    Immutable: every transform returns a new IDMapper.
    """

    visual_order: np.ndarray
    gap_positions: frozenset[int] = field(default_factory=frozenset)
    groups: tuple[SplitGroup, ...] = ()

    @classmethod
    def from_ids(cls, ids: np.ndarray | list) -> IDMapper:
        """Create an IDMapper from an ordered sequence of IDs (no splits)."""
        arr = np.asarray(ids, dtype=object)
        if len(arr) == 0:
            raise ValueError("Cannot create IDMapper from empty ID list.")
        if len(set(arr.tolist())) != len(arr):
            raise ValueError("IDs must be unique.")
        return cls(
            visual_order=arr,
            groups=(SplitGroup(name="__all__", ids=arr),),
        )

    @property
    def size(self) -> int:
        """Number of IDs in the visual order."""
        return len(self.visual_order)

    @property
    def original_ids(self) -> set:
        """Set of all original IDs."""
        return set(self.visual_order.tolist())

    def visual_index_of(self, original_id: object) -> int | None:
        """Return the visual index of an original ID, or None if not found."""
        matches = np.where(self.visual_order == original_id)[0]
        if len(matches) == 0:
            return None
        return int(matches[0])

    def resolve_range(self, start: int, end: int) -> list:
        """Given visual index range [start, end), return original IDs.

        This is the core of the ruler problem solution. O(range_size).
        """
        start = max(0, start)
        end = min(self.size, end)
        if start >= end:
            return []
        return self.visual_order[start:end].tolist()

    def apply_reorder(self, new_order: np.ndarray) -> IDMapper:
        """Return a new IDMapper with IDs reordered.

        new_order must be a permutation of the current visual_order.
        """
        current_set = set(self.visual_order.tolist())
        new_set = set(new_order.tolist())
        if current_set != new_set:
            raise ValueError("new_order must contain exactly the same IDs.")
        return IDMapper(
            visual_order=np.asarray(new_order, dtype=object),
            gap_positions=self.gap_positions,
            groups=self.groups,
        )

    def apply_splits(
        self, assignments: dict[str, list]
    ) -> IDMapper:
        """Split IDs into groups, inserting gaps between them.

        Parameters
        ----------
        assignments : {group_name: [ids]} mapping. Every ID must appear
                      exactly once across all groups.

        Returns a new IDMapper with groups ordered as given and gap
        positions marking group boundaries.
        """
        # Validate all IDs accounted for
        all_assigned = []
        for ids in assignments.values():
            all_assigned.extend(ids)
        assigned_set = set(all_assigned)
        if len(all_assigned) != len(assigned_set):
            raise ValueError("Some IDs appear in multiple split groups.")
        if assigned_set != self.original_ids:
            missing = self.original_ids - assigned_set
            extra = assigned_set - self.original_ids
            parts = []
            if missing:
                parts.append(f"missing: {list(missing)[:5]}")
            if extra:
                parts.append(f"extra: {list(extra)[:5]}")
            raise ValueError(f"Split assignments don't match IDs. {', '.join(parts)}")

        groups: list[SplitGroup] = []
        new_order: list = []
        gap_pos: set[int] = set()

        for name, ids in assignments.items():
            # Preserve relative order from current visual_order within each group
            id_set = set(ids)
            ordered = [x for x in self.visual_order.tolist() if x in id_set]
            if new_order:
                gap_pos.add(len(new_order))
            groups.append(SplitGroup(name=name, ids=np.array(ordered, dtype=object)))
            new_order.extend(ordered)

        return IDMapper(
            visual_order=np.array(new_order, dtype=object),
            gap_positions=frozenset(gap_pos),
            groups=tuple(groups),
        )

    def apply_reorder_within_groups(
        self,
        group_orders: dict[str, np.ndarray],
    ) -> IDMapper:
        """Reorder IDs within each split group independently.

        Parameters
        ----------
        group_orders : {group_name: new_id_order_array}
            Each value must be a permutation of the group's current IDs.
            Groups not present in the dict are left unchanged.

        Returns a new IDMapper with updated visual_order and groups.
        """
        new_visual: list = []
        new_groups: list[SplitGroup] = []

        for group in self.groups:
            if group.name in group_orders:
                new_order = np.asarray(group_orders[group.name], dtype=object)
                # Validate it's a permutation of the group's IDs
                if set(new_order.tolist()) != set(group.ids.tolist()):
                    raise ValueError(
                        f"Reorder for group '{group.name}' doesn't match "
                        f"the group's IDs."
                    )
                new_groups.append(SplitGroup(name=group.name, ids=new_order))
                new_visual.extend(new_order.tolist())
            else:
                new_groups.append(group)
                new_visual.extend(group.ids.tolist())

        return IDMapper(
            visual_order=np.array(new_visual, dtype=object),
            gap_positions=self.gap_positions,
            groups=tuple(new_groups),
        )

    def apply_zoom(self, start: int, end: int) -> IDMapper:
        """Return a new IDMapper for the zoomed-in range [start, end)."""
        start = max(0, start)
        end = min(self.size, end)
        if start >= end:
            raise ValueError(f"Invalid zoom range [{start}, {end}).")
        zoomed = self.visual_order[start:end]
        # Adjust gap positions
        new_gaps = frozenset(
            g - start for g in self.gap_positions if start < g < end
        )
        return IDMapper(
            visual_order=zoomed,
            gap_positions=new_gaps,
            groups=self.groups,  # keep original group info
        )

    def apply_zoom_by_ids(self, ids: list) -> IDMapper:
        """Return a new IDMapper containing only the specified IDs.

        Preserves their current visual order. No gap positions in the
        filtered view (IDs are packed together).
        """
        id_set = set(ids)
        filtered = np.array(
            [x for x in self.visual_order.tolist() if x in id_set],
            dtype=object,
        )
        if len(filtered) == 0:
            raise ValueError("No matching IDs found in visual order.")
        return IDMapper(
            visual_order=filtered,
            gap_positions=frozenset(),
            groups=self.groups,  # keep original group info
        )

    def to_dict(self) -> dict:
        """Serialize for JSON transfer to JS."""
        return {
            "visual_order": self.visual_order.tolist(),
            "gap_positions": sorted(self.gap_positions),
            "size": self.size,
        }
