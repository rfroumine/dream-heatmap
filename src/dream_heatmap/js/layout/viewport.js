/**
 * Viewport: coordinate transforms for zoom/pan state.
 *
 * Tracks the current zoom range (row/col visual index ranges)
 * and provides methods to map between zoomed and full coordinates.
 */

class Viewport {
  constructor() {
    this._rowStart = 0;
    this._rowEnd = 0;
    this._colStart = 0;
    this._colEnd = 0;
    this._isZoomed = false;
  }

  /** @returns {boolean} whether the viewport is zoomed in */
  get isZoomed() { return this._isZoomed; }

  /** @returns {{rowStart: number, rowEnd: number, colStart: number, colEnd: number}} */
  get range() {
    return {
      rowStart: this._rowStart,
      rowEnd: this._rowEnd,
      colStart: this._colStart,
      colEnd: this._colEnd,
    };
  }

  /**
   * Set the zoom range (visual index ranges).
   * @param {number} rowStart
   * @param {number} rowEnd
   * @param {number} colStart
   * @param {number} colEnd
   */
  setRange(rowStart, rowEnd, colStart, colEnd) {
    this._rowStart = rowStart;
    this._rowEnd = rowEnd;
    this._colStart = colStart;
    this._colEnd = colEnd;
    this._isZoomed = true;
  }

  /** Reset to full view. */
  reset() {
    this._rowStart = 0;
    this._rowEnd = 0;
    this._colStart = 0;
    this._colEnd = 0;
    this._isZoomed = false;
  }
}
