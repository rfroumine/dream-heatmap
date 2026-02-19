/**
 * PanelModelSync: adapts Panel JSComponent model to the interface
 * expected by the dream-heatmap JS renderer (matches ModelSync API).
 *
 * Panel uses property access (model.X) and model.on('X', cb),
 * vs anywidget's model.get('X') and model.on('change:X', cb).
 * Binary data is transferred as base64 strings instead of raw bytes.
 */

function b64ToArrayBuffer(b64) {
  const bin = atob(b64);
  const len = bin.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

class PanelModelSync {
  constructor(model) {
    this._model = model;
  }

  /** @returns {ArrayBuffer} decoded matrix bytes from base64 */
  getMatrixBytes() {
    const b64 = this._model.matrix_b64;
    if (!b64) return new ArrayBuffer(0);
    return b64ToArrayBuffer(b64);
  }

  /** @returns {ArrayBuffer} decoded color LUT bytes from base64 */
  getColorLUT() {
    const b64 = this._model.color_lut_b64;
    if (!b64) return new ArrayBuffer(0);
    return b64ToArrayBuffer(b64);
  }

  /** @returns {object} parsed layout specification */
  getLayout() {
    const raw = this._model.layout_json;
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  /** @returns {object} parsed IDMapper data {row, col} */
  getIDMappers() {
    const raw = this._model.id_mappers_json;
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  /** @returns {object} parsed config */
  getConfig() {
    const raw = this._model.config_json;
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  /**
   * Send selection back to Python.
   * @param {object} selection - {row_ids: [...], col_ids: [...]}
   */
  setSelection(selection) {
    this._model.selection_json = JSON.stringify(selection);
  }

  /**
   * Send zoom range to Python.
   * @param {object|null} range - {row_start, row_end, col_start, col_end} or null
   */
  setZoomRange(range) {
    this._model.zoom_range_json = JSON.stringify(range);
  }

  /**
   * Register a callback for when any data property changes.
   * @param {function} callback
   */
  onChange(callback) {
    for (const prop of ["matrix_b64", "color_lut_b64", "layout_json", "id_mappers_json", "config_json"]) {
      this._model.on(prop, callback);
    }
  }
}
