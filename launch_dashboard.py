"""Launch the dream-heatmap dashboard with TME expression data."""

import pandas as pd
import dream_heatmap as dh

expr = pd.read_csv("data/tme_expression_matrix.csv", index_col=0)
meta = pd.read_csv("data/tme_cell_metadata.csv").set_index("cell_id")

print(f"Expression matrix: {expr.shape[0]} markers x {expr.shape[1]} cells")
print(f"Metadata columns: {list(meta.columns)}")
print("Launching dashboard...")

dh.explore(expr, col_metadata=meta)
