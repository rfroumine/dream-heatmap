"""Integration test: full dummy scenario from the spec.

16 genes x 10 patients → clustering + annotations → rectangle select
→ verify IDs → zoom → verify alignment → splits + reorder → concatenate.
"""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.api import Heatmap
from dream_heatmap.annotation.categorical import CategoricalAnnotation
from dream_heatmap.annotation.minigraph import BarChartAnnotation
from dream_heatmap.annotation.label import LabelAnnotation
from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.concat.heatmap_list import HeatmapList


# --- Fixtures ---

@pytest.fixture
def gene_patient_data():
    """16 genes x 10 patients, with metadata."""
    rng = np.random.default_rng(42)
    genes = [f"gene_{i:02d}" for i in range(16)]
    patients = [f"patient_{j:02d}" for j in range(10)]
    matrix = pd.DataFrame(
        rng.standard_normal((16, 10)),
        index=genes,
        columns=patients,
    )
    row_meta = pd.DataFrame(
        {
            "cell_type": (["T-cell"] * 4 + ["B-cell"] * 4 +
                          ["NK-cell"] * 4 + ["Monocyte"] * 4),
            "expression": rng.uniform(0, 10, 16),
        },
        index=genes,
    )
    col_meta = pd.DataFrame(
        {
            "treatment": (["control"] * 5 + ["drug_A"] * 5),
            "batch": (["batch1"] * 3 + ["batch2"] * 3 + ["batch1"] * 2 + ["batch2"] * 2),
        },
        index=patients,
    )
    return matrix, row_meta, col_meta


# --- IDMapper Invariants ---

def assert_mapper_invariants(mapper: IDMapper, expected_ids: set):
    """Verify critical IDMapper invariants."""
    actual_ids = set(mapper.visual_order.tolist())
    assert actual_ids == expected_ids, "ID set mismatch after transform"
    assert len(mapper.visual_order) == len(expected_ids), "Duplicate IDs detected"
    # All gap positions within bounds
    for gap in mapper.gap_positions:
        assert 0 < gap < mapper.size, f"Gap position {gap} out of range [1, {mapper.size - 1}]"


# --- Full Integration ---

class TestFullIntegration:
    def test_basic_heatmap(self, gene_patient_data):
        """Plain heatmap with no transforms."""
        matrix, _, _ = gene_patient_data
        hm = Heatmap(matrix)
        hm.set_colormap("viridis")
        hm._compute_layout()
        assert hm._layout is not None
        assert hm._layout.n_rows == 16
        assert hm._layout.n_cols == 10

    def test_with_clustering(self, gene_patient_data):
        """Cluster both axes."""
        matrix, _, _ = gene_patient_data
        hm = Heatmap(matrix)
        hm.cluster_rows(method="ward", metric="euclidean")
        hm.cluster_cols(method="average", metric="correlation")

        # IDMapper invariants
        assert_mapper_invariants(hm._row_mapper, set(matrix.index))
        assert_mapper_invariants(hm._col_mapper, set(matrix.columns))

        # Cluster results exist
        assert hm._row_cluster is not None
        assert hm._col_cluster is not None

    def test_split_then_cluster(self, gene_patient_data):
        """Split rows by cell_type, then cluster within groups."""
        matrix, row_meta, _ = gene_patient_data
        hm = Heatmap(matrix)
        hm.set_row_metadata(row_meta)
        hm.split_rows(by="cell_type")

        # Should have 3 gaps (4 groups)
        assert len(hm._row_mapper.gap_positions) == 3
        assert_mapper_invariants(hm._row_mapper, set(matrix.index))

        hm.cluster_rows(method="average", metric="euclidean")
        assert_mapper_invariants(hm._row_mapper, set(matrix.index))

        # Each group should be independently clustered
        assert len(hm._row_cluster) == 4

    def test_split_then_reorder(self, gene_patient_data):
        """Split by cell_type, reorder by expression."""
        matrix, row_meta, _ = gene_patient_data
        hm = Heatmap(matrix)
        hm.set_row_metadata(row_meta)
        hm.split_rows(by="cell_type")
        hm.order_rows(by="expression")

        assert_mapper_invariants(hm._row_mapper, set(matrix.index))

    def test_annotations(self, gene_patient_data):
        """Add annotations to all edges."""
        matrix, row_meta, col_meta = gene_patient_data
        hm = Heatmap(matrix)
        hm.set_row_metadata(row_meta)
        hm.set_col_metadata(col_meta)

        # Left: categorical
        hm.add_annotation("left", CategoricalAnnotation(
            "cell_type", row_meta["cell_type"]
        ))
        # Right: bar chart
        hm.add_annotation("right", BarChartAnnotation(
            "expression", row_meta["expression"]
        ))
        # Top: categorical
        hm.add_annotation("top", CategoricalAnnotation(
            "treatment", col_meta["treatment"]
        ))
        # Bottom: label
        hm.add_annotation("bottom", LabelAnnotation("batch"))

        hm._compute_layout()
        ann_data = hm._build_annotation_data()
        assert ann_data is not None
        assert "left" in ann_data
        assert "right" in ann_data
        assert "top" in ann_data
        assert "bottom" in ann_data

    def test_labels(self, gene_patient_data):
        """Label display modes."""
        matrix, _, _ = gene_patient_data
        hm = Heatmap(matrix)

        hm.set_label_display(rows="all", cols="auto")
        hm._compute_layout()
        label_data = hm._build_label_data()
        assert label_data is not None
        assert len(label_data["row"]["labels"]) == 16
        assert all(l["visible"] for l in label_data["row"]["labels"])

    def test_selection_roundtrip(self, gene_patient_data):
        """Select a range and verify IDs."""
        matrix, _, _ = gene_patient_data
        hm = Heatmap(matrix)
        hm._compute_layout()

        # Select rows 2-5 (0-indexed visual positions)
        selected = hm._row_mapper.resolve_range(2, 6)
        assert len(selected) == 4
        # All selected IDs should be in the original set
        assert all(sid in set(matrix.index) for sid in selected)

    def test_zoom(self, gene_patient_data):
        """Zoom into a subset and verify."""
        matrix, _, _ = gene_patient_data
        hm = Heatmap(matrix)
        hm._compute_layout()

        zoomed_row = hm._row_mapper.apply_zoom(2, 8)
        zoomed_col = hm._col_mapper.apply_zoom(1, 5)
        assert zoomed_row.size == 6
        assert zoomed_col.size == 4
        # Zoomed IDs are a subset
        assert set(zoomed_row.visual_order.tolist()).issubset(set(matrix.index))
        assert set(zoomed_col.visual_order.tolist()).issubset(set(matrix.columns))

    def test_concatenation(self, gene_patient_data):
        """Horizontal concatenation of two heatmaps."""
        matrix, row_meta, col_meta = gene_patient_data

        # Split columns into two matrices
        ctrl_cols = [c for c in matrix.columns if col_meta.loc[c, "treatment"] == "control"]
        drug_cols = [c for c in matrix.columns if col_meta.loc[c, "treatment"] == "drug_A"]

        hm1 = Heatmap(matrix[ctrl_cols])
        hm2 = Heatmap(matrix[drug_cols])

        combined = Heatmap.hconcat(hm1, hm2)
        assert isinstance(combined, HeatmapList)
        assert combined.direction == "horizontal"

        # Cross-boundary selection
        comp = combined.composite_mapper
        result = comp.resolve_range(3, 7)
        # Should span both panels
        total_ids = sum(len(ids) for ids in result.values())
        assert total_ids == 4

    def test_full_pipeline(self, gene_patient_data):
        """Full pipeline: metadata → split → cluster → annotate → label → layout."""
        matrix, row_meta, col_meta = gene_patient_data
        hm = Heatmap(matrix)
        hm.set_row_metadata(row_meta)
        hm.set_col_metadata(col_meta)
        hm.set_colormap("plasma", vmin=-3, vmax=3)
        hm.split_rows(by="cell_type")
        hm.cluster_rows(method="ward")
        hm.cluster_cols(method="average", metric="correlation")
        hm.add_annotation("left", CategoricalAnnotation("ct", row_meta["cell_type"]))
        hm.add_annotation("right", BarChartAnnotation("expr", row_meta["expression"]))
        hm.add_annotation("top", CategoricalAnnotation("tx", col_meta["treatment"]))
        hm.set_label_display(rows="auto", cols="all")

        # Verify invariants after all transforms
        assert_mapper_invariants(hm._row_mapper, set(matrix.index))
        assert_mapper_invariants(hm._col_mapper, set(matrix.columns))

        # Compute layout
        hm._compute_layout()
        assert hm._layout is not None
        assert hm._layout.total_width > 0
        assert hm._layout.total_height > 0
        assert hm._layout.row_dendro_width > 0  # clustered rows
        assert hm._layout.col_dendro_height > 0  # clustered cols

        # Build all render data
        dendro = hm._build_dendrogram_data()
        assert dendro is not None
        assert "row" in dendro
        assert "col" in dendro

        ann = hm._build_annotation_data()
        assert ann is not None
        assert len(ann) == 3  # left, right, top

        labels = hm._build_label_data()
        assert labels is not None


# --- Edge Cases ---

class TestEdgeCases:
    def test_nan_matrix(self):
        """Matrix with NaN values should work."""
        df = pd.DataFrame(
            [[1.0, np.nan], [np.nan, 4.0]],
            index=["r1", "r2"],
            columns=["c1", "c2"],
        )
        hm = Heatmap(df)
        hm.cluster_rows()
        hm._compute_layout()
        assert hm._layout is not None

    def test_single_row(self):
        """Single-row matrix."""
        df = pd.DataFrame(
            [[1.0, 2.0, 3.0]],
            index=["only_row"],
            columns=["c1", "c2", "c3"],
        )
        hm = Heatmap(df)
        hm._compute_layout()
        assert hm._layout.n_rows == 1
        # Clustering single row should work (no-op)
        hm.cluster_rows()
        assert_mapper_invariants(hm._row_mapper, {"only_row"})

    def test_single_col(self):
        """Single-column matrix."""
        df = pd.DataFrame(
            [[1.0], [2.0], [3.0]],
            index=["r1", "r2", "r3"],
            columns=["only_col"],
        )
        hm = Heatmap(df)
        hm._compute_layout()
        assert hm._layout.n_cols == 1

    def test_empty_selection(self):
        """Empty selection returns empty lists."""
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert mapper.resolve_range(5, 10) == []
        assert mapper.resolve_range(2, 0) == []

    def test_large_matrix(self):
        """100x50 matrix smoke test."""
        rng = np.random.default_rng(123)
        df = pd.DataFrame(
            rng.standard_normal((100, 50)),
            index=[f"g{i}" for i in range(100)],
            columns=[f"s{j}" for j in range(50)],
        )
        hm = Heatmap(df)
        hm.cluster_rows()
        hm.cluster_cols()
        hm._compute_layout()

        assert_mapper_invariants(hm._row_mapper, set(df.index))
        assert_mapper_invariants(hm._col_mapper, set(df.columns))

        # Selection within clustered matrix
        selected_rows = hm._row_mapper.resolve_range(10, 20)
        assert len(selected_rows) == 10

    def test_html_export_roundtrip(self, tmp_path):
        """Export to HTML and verify file is created."""
        df = pd.DataFrame(
            np.arange(6, dtype=float).reshape(2, 3),
            index=["r1", "r2"],
            columns=["c1", "c2", "c3"],
        )
        hm = Heatmap(df)
        out = tmp_path / "test.html"
        hm.to_html(str(out))
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "CanvasRenderer" in content
        assert "MATRIX_B64" in content

    def test_builder_pattern_chaining(self):
        """All builder methods return self for chaining."""
        df = pd.DataFrame(
            np.arange(12, dtype=float).reshape(4, 3),
            index=["g1", "g2", "g3", "g4"],
            columns=["s1", "s2", "s3"],
        )
        meta = pd.DataFrame(
            {"group": ["A", "A", "B", "B"]},
            index=["g1", "g2", "g3", "g4"],
        )
        hm = (
            Heatmap(df)
            .set_row_metadata(meta)
            .set_colormap("plasma")
            .split_rows(by="group")
            .cluster_rows()
            .set_label_display(rows="all", cols="none")
        )
        assert isinstance(hm, Heatmap)
        assert_mapper_invariants(hm._row_mapper, {"g1", "g2", "g3", "g4"})


class TestDendrogramSide:
    """Test dendrogram side placement via set_dendro_side()."""

    def test_default_side(self, gene_patient_data):
        df, row_meta, col_meta = gene_patient_data
        hm = Heatmap(df).cluster_rows().cluster_cols()
        hm._compute_layout()
        dendro_data = hm._build_dendrogram_data()
        assert dendro_data["row"]["side"] == "left"
        assert dendro_data["col"]["side"] == "top"

    def test_right_row_dendro(self, gene_patient_data):
        df, row_meta, col_meta = gene_patient_data
        hm = Heatmap(df).set_dendro_side(row_side="right").cluster_rows()
        hm._compute_layout()
        dendro_data = hm._build_dendrogram_data()
        assert dendro_data["row"]["side"] == "right"
        assert hm._layout.row_dendro_side == "right"

    def test_bottom_col_dendro(self, gene_patient_data):
        df, row_meta, col_meta = gene_patient_data
        hm = Heatmap(df).set_dendro_side(col_side="bottom").cluster_cols()
        hm._compute_layout()
        dendro_data = hm._build_dendrogram_data()
        assert dendro_data["col"]["side"] == "bottom"
        assert hm._layout.col_dendro_side == "bottom"

    def test_invalid_side_raises(self, gene_patient_data):
        df, row_meta, col_meta = gene_patient_data
        hm = Heatmap(df)
        with pytest.raises(ValueError, match="row_side must be"):
            hm.set_dendro_side(row_side="top")
        with pytest.raises(ValueError, match="col_side must be"):
            hm.set_dendro_side(col_side="left")
