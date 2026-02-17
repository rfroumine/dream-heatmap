/**
 * Binary data decoders for transferring matrix data from Python.
 */

/**
 * Decode a row-major float64 byte buffer into a Float64Array.
 * @param {ArrayBuffer|DataView|Uint8Array} buffer
 * @returns {Float64Array}
 */
function decodeMatrixBytes(buffer) {
  if (buffer instanceof Uint8Array) {
    // Ensure aligned access
    const aligned = new ArrayBuffer(buffer.byteLength);
    new Uint8Array(aligned).set(buffer);
    return new Float64Array(aligned);
  }
  if (buffer instanceof DataView) {
    return new Float64Array(buffer.buffer, buffer.byteOffset, buffer.byteLength / 8);
  }
  return new Float64Array(buffer);
}

/**
 * Decode a 1024-byte color LUT into a Uint8Array of [R,G,B,A, R,G,B,A, ...].
 * @param {ArrayBuffer|DataView|Uint8Array} buffer
 * @returns {Uint8Array} 256*4 = 1024 bytes
 */
function decodeColorLUT(buffer) {
  if (buffer instanceof Uint8Array) {
    return buffer;
  }
  if (buffer instanceof DataView) {
    return new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  }
  return new Uint8Array(buffer);
}
