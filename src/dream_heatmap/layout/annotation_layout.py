"""Annotation track positioning alongside the heatmap."""

from __future__ import annotations

from dataclasses import dataclass

from ..annotation.base import AnnotationTrack, DEFAULT_TRACK_GAP


MAX_TRACKS_PER_EDGE = 3


@dataclass(frozen=True)
class AnnotationTrackSpec:
    """Pixel position of one annotation track."""

    name: str
    edge: str           # "left", "right", "top", "bottom"
    offset: float       # pixel offset from heatmap edge (outward)
    track_width: float  # pixel width of this track
    render_data: dict   # serialized data for JS rendering


class AnnotationLayoutEngine:
    """Computes annotation track positions for one or more edges.

    Tracks stack outward from the heatmap edge with a small gap
    between each track.
    """

    @staticmethod
    def compute_edge_tracks(
        tracks: list[AnnotationTrack],
        edge: str,
        visual_order,
    ) -> list[AnnotationTrackSpec]:
        """Compute track specs for all annotations on one edge.

        Parameters
        ----------
        tracks : list of AnnotationTrack
        edge : "left", "right", "top", or "bottom"
        visual_order : array of IDs in current visual order

        Returns list of AnnotationTrackSpec with pixel offsets.
        """
        specs = []
        current_offset = DEFAULT_TRACK_GAP

        for track in tracks:
            render_data = track.get_render_data(visual_order)
            specs.append(AnnotationTrackSpec(
                name=track.name,
                edge=edge,
                offset=current_offset,
                track_width=track.track_width,
                render_data=render_data,
            ))
            current_offset += track.track_width + DEFAULT_TRACK_GAP

        return specs

    @staticmethod
    def total_edge_width(tracks: list[AnnotationTrack]) -> float:
        """Total pixel width needed for all tracks on one edge."""
        if not tracks:
            return 0.0
        total = DEFAULT_TRACK_GAP  # initial gap
        for track in tracks:
            total += track.track_width + DEFAULT_TRACK_GAP
        return total
