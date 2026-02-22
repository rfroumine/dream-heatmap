"""Generate biologically realistic HER2+ TME single-cell protein expression data.

Produces three CSV files used by the tumor_microenvironment.ipynb notebook:
- tme_expression_matrix.csv  (20 markers × 5000 cells)
- tme_cell_metadata.csv      (cell_id, cell_type, subtype, patient_id, tissue_region)
- tme_marker_metadata.csv    (marker, positivity_cutoff)

Models within-type heterogeneity (2-3 subtypes per cell type), marker-aware noise,
realistic TME cell proportions, and tissue region assignment.

No dream-heatmap dependency — only numpy + pandas.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEED = 42
N_PATIENTS = 20
TOTAL_CELLS = 5000
BATCH_STD = 0.05

MARKERS = [
    "HER2", "CK", "Ki67", "EGFR", "E-cadherin", "p53",
    "CD45", "CD8", "CD4", "FOXP3", "CD20", "CD56",
    "CD68", "CD11c", "PD-L1", "PD-1", "SMA", "Vimentin",
    "Collagen", "CD31",
]

# Marker indices for quick reference
_M = {name: i for i, name in enumerate(MARKERS)}

# ---------------------------------------------------------------------------
# Marker-aware noise model
# ---------------------------------------------------------------------------
# Different noise levels by marker category.
# (positive_std, background_std) — positive_std used when archetype > 0.20,
# background_std when archetype <= 0.20.

MARKER_NOISE = {}

_LINEAGE = ["CD8", "CD4", "CD20", "CD56", "CD68", "CD11c", "CD31", "CD45"]
_STRUCTURAL = ["CK", "E-cadherin", "SMA", "Collagen", "Vimentin", "HER2"]
_FUNCTIONAL = ["Ki67", "PD-1", "PD-L1", "p53", "FOXP3", "EGFR"]

for m in _LINEAGE:
    MARKER_NOISE[m] = (0.06, 0.04)
for m in _STRUCTURAL:
    MARKER_NOISE[m] = (0.07, 0.04)
for m in _FUNCTIONAL:
    MARKER_NOISE[m] = (0.12, 0.05)

# ---------------------------------------------------------------------------
# Cell type proportions (of TOTAL_CELLS)
# ---------------------------------------------------------------------------

CELL_TYPE_PROPORTIONS = {
    "HER2+ Tumor": 0.30,
    "Macrophage": 0.15,
    "CD8+ T cell": 0.12,
    "CD4+ T cell": 0.10,
    "CAF": 0.10,
    "Treg": 0.06,
    "B cell": 0.06,
    "NK cell": 0.04,
    "Dendritic cell": 0.04,
    "Endothelial": 0.03,
}

# ---------------------------------------------------------------------------
# Subtype definitions
# ---------------------------------------------------------------------------
# Each cell type has 2-3 subtypes. Each subtype has:
#   - name: display name
#   - proportion: fraction within the cell type
#   - archetype: 20-marker expression vector (same order as MARKERS)
#
# Archetype values in [0, 1]:
#   "High" ~ 0.75-0.90, "Medium" ~ 0.35-0.55, "Low/Background" ~ 0.03-0.10
#
# Marker order:
# HER2  CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FOXP3 CD20 CD56 CD68 CD11c PDL1 PD1  SMA  Vim  Coll CD31

SUBTYPES = {
    "HER2+ Tumor": [
        {
            "name": "Proliferating",
            "proportion": 0.40,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.88, 0.82, 0.75, 0.68, 0.78, 0.65, 0.05, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.28, 0.05, 0.06, 0.08, 0.04, 0.03],
        },
        {
            "name": "Quiescent",
            "proportion": 0.40,
            "arch": [0.82, 0.78, 0.12, 0.60, 0.80, 0.30, 0.05, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.30, 0.05, 0.08, 0.10, 0.05, 0.03],
        },
        {
            "name": "EMT",
            "proportion": 0.20,
            "arch": [0.70, 0.45, 0.40, 0.55, 0.25, 0.50, 0.05, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.35, 0.05, 0.15, 0.55, 0.10, 0.03],
        },
    ],
    "CD8+ T cell": [
        {
            "name": "Effector",
            "proportion": 0.25,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.03, 0.03, 0.45, 0.04, 0.03, 0.05, 0.88, 0.88, 0.05, 0.05, 0.03, 0.15, 0.03, 0.03, 0.08, 0.20, 0.03, 0.04, 0.03, 0.03],
        },
        {
            "name": "Exhausted",
            "proportion": 0.55,
            "arch": [0.03, 0.03, 0.10, 0.04, 0.03, 0.05, 0.85, 0.85, 0.05, 0.08, 0.03, 0.12, 0.03, 0.03, 0.10, 0.72, 0.03, 0.04, 0.03, 0.03],
        },
        {
            "name": "Tissue-Resident Memory",
            "proportion": 0.20,
            "arch": [0.03, 0.03, 0.15, 0.04, 0.03, 0.05, 0.82, 0.82, 0.05, 0.06, 0.03, 0.20, 0.03, 0.03, 0.06, 0.35, 0.03, 0.04, 0.03, 0.03],
        },
    ],
    "CD4+ T cell": [
        {
            "name": "Th1-like",
            "proportion": 0.50,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.03, 0.03, 0.25, 0.04, 0.03, 0.05, 0.85, 0.05, 0.82, 0.08, 0.03, 0.05, 0.03, 0.03, 0.06, 0.35, 0.03, 0.04, 0.03, 0.03],
        },
        {
            "name": "Activated",
            "proportion": 0.30,
            "arch": [0.03, 0.03, 0.40, 0.04, 0.03, 0.05, 0.85, 0.05, 0.80, 0.10, 0.03, 0.05, 0.03, 0.03, 0.08, 0.42, 0.03, 0.04, 0.03, 0.03],
        },
        {
            "name": "Resting",
            "proportion": 0.20,
            "arch": [0.03, 0.03, 0.08, 0.04, 0.03, 0.05, 0.80, 0.05, 0.78, 0.06, 0.03, 0.05, 0.03, 0.03, 0.05, 0.15, 0.03, 0.04, 0.03, 0.03],
        },
    ],
    "Treg": [
        {
            "name": "Activated Treg",
            "proportion": 0.65,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.03, 0.03, 0.35, 0.04, 0.03, 0.05, 0.82, 0.05, 0.76, 0.85, 0.03, 0.03, 0.03, 0.03, 0.10, 0.50, 0.03, 0.04, 0.03, 0.03],
        },
        {
            "name": "Resting Treg",
            "proportion": 0.35,
            "arch": [0.03, 0.03, 0.10, 0.04, 0.03, 0.05, 0.78, 0.05, 0.72, 0.75, 0.03, 0.03, 0.03, 0.03, 0.08, 0.30, 0.03, 0.04, 0.03, 0.03],
        },
    ],
    "B cell": [
        {
            "name": "Activated B cell",
            "proportion": 0.35,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.03, 0.03, 0.35, 0.04, 0.03, 0.05, 0.82, 0.05, 0.05, 0.03, 0.88, 0.03, 0.03, 0.03, 0.08, 0.10, 0.03, 0.04, 0.03, 0.03],
        },
        {
            "name": "Resting B cell",
            "proportion": 0.65,
            "arch": [0.03, 0.03, 0.08, 0.04, 0.03, 0.05, 0.78, 0.05, 0.05, 0.03, 0.82, 0.03, 0.03, 0.03, 0.05, 0.04, 0.03, 0.04, 0.03, 0.03],
        },
    ],
    "NK cell": [
        {
            "name": "CD56bright NK",
            "proportion": 0.30,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.03, 0.03, 0.35, 0.04, 0.03, 0.05, 0.80, 0.10, 0.05, 0.03, 0.03, 0.90, 0.03, 0.03, 0.08, 0.10, 0.03, 0.04, 0.03, 0.03],
        },
        {
            "name": "CD56dim NK",
            "proportion": 0.70,
            "arch": [0.03, 0.03, 0.25, 0.04, 0.03, 0.05, 0.75, 0.12, 0.05, 0.03, 0.03, 0.78, 0.03, 0.03, 0.10, 0.18, 0.03, 0.04, 0.03, 0.03],
        },
    ],
    "Macrophage": [
        {
            "name": "M1-like",
            "proportion": 0.35,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.03, 0.03, 0.20, 0.10, 0.03, 0.05, 0.82, 0.03, 0.05, 0.03, 0.03, 0.03, 0.85, 0.45, 0.55, 0.05, 0.04, 0.18, 0.04, 0.03],
        },
        {
            "name": "M2-like TAM",
            "proportion": 0.65,
            "arch": [0.03, 0.03, 0.12, 0.12, 0.03, 0.05, 0.78, 0.03, 0.05, 0.03, 0.03, 0.03, 0.82, 0.20, 0.70, 0.05, 0.05, 0.22, 0.05, 0.03],
        },
    ],
    "Dendritic cell": [
        {
            "name": "Mature DC",
            "proportion": 0.40,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.03, 0.03, 0.18, 0.05, 0.03, 0.05, 0.80, 0.03, 0.05, 0.03, 0.03, 0.03, 0.18, 0.88, 0.45, 0.05, 0.03, 0.08, 0.03, 0.03],
        },
        {
            "name": "Immature DC",
            "proportion": 0.60,
            "arch": [0.03, 0.03, 0.10, 0.05, 0.03, 0.05, 0.75, 0.03, 0.05, 0.03, 0.03, 0.03, 0.15, 0.82, 0.30, 0.05, 0.03, 0.10, 0.03, 0.03],
        },
    ],
    "CAF": [
        {
            "name": "myCAF",
            "proportion": 0.50,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.04, 0.06, 0.08, 0.04, 0.04, 0.04, 0.04, 0.03, 0.03, 0.03, 0.03, 0.03, 0.04, 0.03, 0.15, 0.04, 0.90, 0.82, 0.85, 0.04],
        },
        {
            "name": "iCAF",
            "proportion": 0.50,
            "arch": [0.04, 0.08, 0.15, 0.05, 0.05, 0.04, 0.05, 0.03, 0.03, 0.03, 0.03, 0.03, 0.04, 0.03, 0.30, 0.04, 0.60, 0.78, 0.72, 0.04],
        },
    ],
    "Endothelial": [
        {
            "name": "Tumor Vasculature",
            "proportion": 0.60,
            #        HER2 CK   Ki67 EGFR Ecad p53  CD45 CD8  CD4  FXP3 CD20 CD56 CD68 CD11 PDL1 PD1  SMA  Vim  Coll CD31
            "arch": [0.04, 0.04, 0.12, 0.05, 0.15, 0.04, 0.08, 0.03, 0.03, 0.03, 0.03, 0.03, 0.04, 0.03, 0.22, 0.04, 0.08, 0.72, 0.10, 0.88],
        },
        {
            "name": "Normal Endothelial",
            "proportion": 0.40,
            "arch": [0.04, 0.04, 0.06, 0.04, 0.18, 0.04, 0.07, 0.03, 0.03, 0.03, 0.03, 0.03, 0.04, 0.03, 0.12, 0.04, 0.07, 0.65, 0.08, 0.85],
        },
    ],
}

# ---------------------------------------------------------------------------
# Tissue region assignment probabilities per cell type
# ---------------------------------------------------------------------------
# {cell_type: {"Tumor core": p, "Invasive margin": p, "Stroma": p}}

REGION_PROBS = {
    "HER2+ Tumor":   {"Tumor core": 0.70, "Invasive margin": 0.25, "Stroma": 0.05},
    "Macrophage":     {"Tumor core": 0.40, "Invasive margin": 0.35, "Stroma": 0.25},
    "CD8+ T cell":    {"Tumor core": 0.25, "Invasive margin": 0.50, "Stroma": 0.25},
    "CD4+ T cell":    {"Tumor core": 0.25, "Invasive margin": 0.50, "Stroma": 0.25},
    "Treg":           {"Tumor core": 0.35, "Invasive margin": 0.40, "Stroma": 0.25},
    "B cell":         {"Tumor core": 0.15, "Invasive margin": 0.45, "Stroma": 0.40},
    "NK cell":        {"Tumor core": 0.20, "Invasive margin": 0.50, "Stroma": 0.30},
    "Dendritic cell": {"Tumor core": 0.20, "Invasive margin": 0.45, "Stroma": 0.35},
    "CAF":            {"Tumor core": 0.15, "Invasive margin": 0.20, "Stroma": 0.65},
    "Endothelial":    {"Tumor core": 0.20, "Invasive margin": 0.25, "Stroma": 0.55},
}

# Per-marker positivity cutoffs (tighter background → lower cutoffs)
CUTOFFS = {
    "HER2": 0.35, "CK": 0.35, "Ki67": 0.25, "EGFR": 0.30, "E-cadherin": 0.30,
    "p53": 0.25, "CD45": 0.30, "CD8": 0.30, "CD4": 0.30, "FOXP3": 0.25,
    "CD20": 0.30, "CD56": 0.30, "CD68": 0.30, "CD11c": 0.30, "PD-L1": 0.25,
    "PD-1": 0.22, "SMA": 0.30, "Vimentin": 0.30, "Collagen": 0.30, "CD31": 0.30,
}

# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _compute_cell_counts(rng):
    """Compute per-type cell counts that sum to TOTAL_CELLS, distributed across patients."""
    counts = {}
    remaining = TOTAL_CELLS
    types = list(CELL_TYPE_PROPORTIONS.keys())

    for i, ct in enumerate(types):
        if i == len(types) - 1:
            counts[ct] = remaining
        else:
            counts[ct] = int(round(CELL_TYPE_PROPORTIONS[ct] * TOTAL_CELLS))
            remaining -= counts[ct]

    return counts


def _assign_noise(archetype_val, marker_name, rng, n):
    """Generate marker-aware noise for n cells."""
    pos_std, bg_std = MARKER_NOISE[marker_name]
    std = pos_std if archetype_val > 0.20 else bg_std
    return rng.normal(0, std, size=n)


def generate():
    rng = np.random.default_rng(SEED)
    out_dir = Path(__file__).parent

    # Pre-compute patient batch effects: (n_patients, n_markers)
    batch_effects = rng.normal(0, BATCH_STD, size=(N_PATIENTS, len(MARKERS)))

    cell_counts = _compute_cell_counts(rng)

    cell_ids = []
    cell_types = []
    subtypes = []
    patient_ids = []
    tissue_regions = []
    match_types = []
    expression_rows = []  # list of 1-D arrays, one per cell

    cell_counter = 0
    region_names = ["Tumor core", "Invasive margin", "Stroma"]

    for cell_type, total_for_type in cell_counts.items():
        type_subtypes = SUBTYPES[cell_type]
        region_prob = REGION_PROBS[cell_type]
        region_weights = [region_prob[r] for r in region_names]

        # Distribute cells across subtypes
        subtype_cells_remaining = total_for_type
        for si, st in enumerate(type_subtypes):
            if si == len(type_subtypes) - 1:
                n_subtype = subtype_cells_remaining
            else:
                n_subtype = int(round(st["proportion"] * total_for_type))
                subtype_cells_remaining -= n_subtype

            archetype = np.array(st["arch"])

            # Distribute across patients (roughly even, with remainder spread)
            base_per_patient = n_subtype // N_PATIENTS
            extra = n_subtype % N_PATIENTS
            patient_alloc = [base_per_patient + (1 if p < extra else 0) for p in range(N_PATIENTS)]

            for patient_idx in range(N_PATIENTS):
                n_cells = patient_alloc[patient_idx]
                if n_cells == 0:
                    continue

                patient_id = f"P{patient_idx + 1:02d}"

                for _ in range(n_cells):
                    cell_counter += 1
                    cell_id = f"cell_{cell_counter:04d}"

                    # Per-marker noise
                    noise = np.array([
                        _assign_noise(archetype[mi], MARKERS[mi], rng, 1)[0]
                        for mi in range(len(MARKERS))
                    ])

                    expr = archetype + batch_effects[patient_idx] + noise
                    expr = np.clip(expr, 0.0, 1.0)

                    # Tissue region assignment
                    region = rng.choice(region_names, p=region_weights)

                    match_type = rng.choice(["perfect", "soft"])

                    cell_ids.append(cell_id)
                    cell_types.append(cell_type)
                    subtypes.append(st["name"])
                    patient_ids.append(patient_id)
                    tissue_regions.append(region)
                    match_types.append(match_type)
                    expression_rows.append(expr)

    # Build expression matrix: markers × cells
    expr_matrix = np.column_stack(expression_rows)  # (n_markers, n_cells)
    expression_df = pd.DataFrame(expr_matrix, index=MARKERS, columns=cell_ids)

    # Cell metadata
    cell_meta_df = pd.DataFrame({
        "cell_id": cell_ids,
        "cell_type": cell_types,
        "subtype": subtypes,
        "patient_id": patient_ids,
        "tissue_region": tissue_regions,
        "match_type": match_types,
    })

    # Marker category and group assignments
    marker_category_map = {
        "HER2": "Tumor", "CK": "Tumor", "Ki67": "Functional", "EGFR": "Tumor",
        "E-cadherin": "Tumor", "p53": "Functional",
        "CD45": "Immune", "CD8": "Immune", "CD4": "Immune", "FOXP3": "Immune",
        "CD20": "Immune", "CD56": "Immune", "CD68": "Immune", "CD11c": "Immune",
        "PD-L1": "Functional", "PD-1": "Functional",
        "SMA": "Stromal", "Vimentin": "Stromal", "Collagen": "Stromal", "CD31": "Stromal",
    }
    marker_group_map = {
        "HER2": "HER2/EGFR", "CK": "Epithelial", "Ki67": "Proliferation", "EGFR": "HER2/EGFR",
        "E-cadherin": "Epithelial", "p53": "Proliferation",
        "CD45": "Pan-immune", "CD8": "T cell", "CD4": "T cell", "FOXP3": "T cell",
        "CD20": "B cell", "CD56": "NK cell", "CD68": "Myeloid", "CD11c": "Myeloid",
        "PD-L1": "Checkpoint", "PD-1": "Checkpoint",
        "SMA": "Structural", "Vimentin": "Structural", "Collagen": "Structural", "CD31": "Vascular",
    }

    # Marker metadata
    marker_meta_df = pd.DataFrame({
        "marker": MARKERS,
        "positivity_cutoff": [CUTOFFS[m] for m in MARKERS],
        "marker_category": [marker_category_map[m] for m in MARKERS],
        "marker_group": [marker_group_map[m] for m in MARKERS],
        "channel_number": list(range(1, len(MARKERS) + 1)),
    })

    # Write CSVs
    expression_df.to_csv(out_dir / "tme_expression_matrix.csv")
    cell_meta_df.to_csv(out_dir / "tme_cell_metadata.csv", index=False)
    marker_meta_df.to_csv(out_dir / "tme_marker_metadata.csv", index=False)

    print(f"Expression matrix: {expression_df.shape[0]} markers x {expression_df.shape[1]} cells")
    print(f"Cell metadata:     {len(cell_meta_df)} rows")
    print(f"  Cell types:      {cell_meta_df['cell_type'].value_counts().to_dict()}")
    print(f"  Subtypes:        {cell_meta_df['subtype'].nunique()} unique")
    print(f"  Tissue regions:  {cell_meta_df['tissue_region'].value_counts().to_dict()}")
    print(f"Marker metadata:   {len(marker_meta_df)} rows")
    print(f"Files written to:  {out_dir}")


if __name__ == "__main__":
    generate()
