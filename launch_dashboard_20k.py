"""Launch dashboard with 20K-cell TME dataset for performance testing."""
import sys
sys.path.insert(0, "data")

import generate_tme_data as gen
import pandas as pd
import dream_heatmap as dh

# Override to 20K cells
gen.TOTAL_CELLS = 20000
gen.generate()

expr = pd.read_csv("data/tme_expression_matrix.csv", index_col=0)
col_meta = pd.read_csv("data/tme_cell_metadata.csv").set_index("cell_id")
row_meta = pd.read_csv("data/tme_marker_metadata.csv").set_index("marker")

dh.explore(expr, row_metadata=row_meta, col_metadata=col_meta)
