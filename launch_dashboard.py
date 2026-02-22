"""Launch the dream-heatmap dashboard with TME expression data."""

import pandas as pd
import dream_heatmap as dh

expr = pd.read_csv("data/tme_expression_matrix.csv", index_col=0)
col_meta = pd.read_csv("data/tme_cell_metadata.csv").set_index("cell_id")
row_meta = pd.read_csv("data/tme_marker_metadata.csv").set_index("marker")

# # print(f"Expression matrix: {expr.shape[0]} markers x {expr.shape[1]} cells")
# print(f"Col metadata columns: {list(col_meta.columns)}")
# print(f"Row metadata columns: {list(row_meta.columns)}")
# print("Launching dashboard...")

dh.explore(expr, row_metadata=row_meta, col_metadata=col_meta)