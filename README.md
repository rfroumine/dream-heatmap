# dream-heatmap

Interactive, table-driven heatmaps that solve the ruler problem.

Draw a rectangle on the heatmap and immediately know which row and column IDs are selected — across clustering, splits, reordering, and concatenated panels.

## Install

```bash
pip install dream-heatmap
```

## Quick Start

```python
import dream_heatmap as dh
import pandas as pd

hm = dh.Heatmap(matrix_df)
hm.set_colormap("viridis")
hm.cluster_rows()
hm.show()

# Selection
print(hm.selection)
hm.on_select(lambda rows, cols: print(rows, cols))
```
