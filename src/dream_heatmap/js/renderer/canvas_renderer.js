/**
 * CanvasRenderer: renders heatmap cells on an HTML5 Canvas.
 * Handles up to 25M cells (5K x 5K) efficiently.
 */

class CanvasRenderer {
  /**
   * @param {HTMLCanvasElement} canvas
   */
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
  }

  /**
   * Render the full heatmap grid.
   *
   * @param {Float64Array} matrix - row-major float64 data
   * @param {object} layout - {rowPositions, colPositions, rowCellSize, colCellSize, nRows, nCols, heatmap}
   * @param {ColorMapper} colorMapper
   */
  render(matrix, layout, colorMapper) {
    const { nRows, nCols, rowPositions, colPositions, rowCellSize, colCellSize } = layout;

    // Size canvas to total layout dimensions
    this.canvas.width = layout.totalWidth;
    this.canvas.height = layout.totalHeight;

    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Use ImageData for efficient pixel manipulation on large matrices
    if (nRows * nCols > 10000) {
      this._renderWithImageData(matrix, layout, colorMapper);
    } else {
      this._renderWithFillRect(matrix, layout, colorMapper);
    }
  }

  /**
   * Fast path: render cells using fillRect (good for small matrices).
   */
  _renderWithFillRect(matrix, layout, colorMapper) {
    const { nRows, nCols, rowPositions, colPositions, rowCellSize, colCellSize } = layout;
    const ctx = this.ctx;

    for (let r = 0; r < nRows; r++) {
      const y = rowPositions[r];
      for (let c = 0; c < nCols; c++) {
        const x = colPositions[c];
        const value = matrix[r * nCols + c];
        const [R, G, B, A] = colorMapper.map(value);
        ctx.fillStyle = `rgba(${R},${G},${B},${A / 255})`;
        ctx.fillRect(x, y, colCellSize, rowCellSize);
      }
    }
  }

  /**
   * Fast path: render using ImageData for large matrices.
   * Writes directly to pixel buffer, then puts the full image.
   */
  _renderWithImageData(matrix, layout, colorMapper) {
    const { nRows, nCols, rowPositions, colPositions, rowCellSize, colCellSize } = layout;
    const width = Math.ceil(layout.totalWidth);
    const height = Math.ceil(layout.totalHeight);

    if (width <= 0 || height <= 0) return;

    const imageData = this.ctx.createImageData(width, height);
    const pixels = imageData.data;

    for (let r = 0; r < nRows; r++) {
      const y0 = Math.floor(rowPositions[r]);
      const y1 = Math.min(Math.ceil(rowPositions[r] + rowCellSize), height);
      for (let c = 0; c < nCols; c++) {
        const x0 = Math.floor(colPositions[c]);
        const x1 = Math.min(Math.ceil(colPositions[c] + colCellSize), width);
        const value = matrix[r * nCols + c];
        const [R, G, B, A] = colorMapper.map(value);

        for (let py = y0; py < y1; py++) {
          for (let px = x0; px < x1; px++) {
            const offset = (py * width + px) * 4;
            pixels[offset] = R;
            pixels[offset + 1] = G;
            pixels[offset + 2] = B;
            pixels[offset + 3] = A;
          }
        }
      }
    }

    this.ctx.putImageData(imageData, 0, 0);
  }
}
