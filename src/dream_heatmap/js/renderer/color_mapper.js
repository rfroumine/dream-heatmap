/**
 * ColorMapper: maps scalar values to RGBA colors via a 256-entry LUT.
 */

class ColorMapper {
  /**
   * @param {Uint8Array} lut - 1024 bytes (256 x RGBA)
   * @param {number} vmin - minimum data value
   * @param {number} vmax - maximum data value
   * @param {number[]} nanColor - [R, G, B, A] for NaN values
   */
  constructor(lut, vmin, vmax, nanColor) {
    this.lut = lut;
    this.vmin = vmin;
    this.vmax = vmax;
    this.range = vmax - vmin;
    this.nanColor = nanColor || [200, 200, 200, 255];
  }

  /**
   * Map a scalar value to [R, G, B, A].
   * @param {number} value
   * @returns {number[]} [R, G, B, A]
   */
  map(value) {
    if (!isFinite(value)) {
      return this.nanColor;
    }
    let normalized;
    if (this.range === 0) {
      normalized = 0.5;
    } else {
      normalized = (value - this.vmin) / this.range;
    }
    // Clamp to [0, 1]
    normalized = Math.max(0, Math.min(1, normalized));
    const index = Math.round(normalized * 255);
    const offset = index * 4;
    return [
      this.lut[offset],
      this.lut[offset + 1],
      this.lut[offset + 2],
      this.lut[offset + 3],
    ];
  }
}
