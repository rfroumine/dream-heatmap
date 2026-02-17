/**
 * Anywidget model wrapper — provides typed access to model traits.
 */

class ModelSync {
  /**
   * @param {object} model - anywidget model object
   */
  constructor(model) {
    this._model = model;
  }

  /** @returns {Uint8Array|ArrayBuffer} raw matrix bytes */
  getMatrixBytes() {
    return this._model.get("matrix_bytes");
  }

  /** @returns {Uint8Array|ArrayBuffer} raw color LUT bytes */
  getColorLUT() {
    return this._model.get("color_lut");
  }

  /** @returns {object} parsed layout specification */
  getLayout() {
    const raw = this._model.get("layout_json");
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  /** @returns {object} parsed IDMapper data {row, col} */
  getIDMappers() {
    const raw = this._model.get("id_mappers_json");
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  /** @returns {object} parsed config */
  getConfig() {
    const raw = this._model.get("config_json");
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  /**
   * Send selection back to Python.
   * @param {object} selection - {row_ids: [...], col_ids: [...]}
   */
  setSelection(selection) {
    this._model.set("selection_json", JSON.stringify(selection));
    this._model.save_changes();
  }

  /**
   * Send zoom range to Python.
   * @param {object|null} range - {row_start, row_end, col_start, col_end} or null to reset
   */
  setZoomRange(range) {
    this._model.set("zoom_range_json", JSON.stringify(range));
    this._model.save_changes();
  }

  /**
   * Register a callback for when any data trait changes.
   * @param {function} callback
   */
  onChange(callback) {
    for (const trait of ["matrix_bytes", "color_lut", "layout_json", "id_mappers_json", "config_json"]) {
      this._model.on(`change:${trait}`, callback);
    }
  }
}
