/* TaxWise TW shield, clean vector (tools/logo_vector.py). viewBox 0 0 1000 1114.1.
 * Three parts so they can animate on their own: the arched T, the W shield, the diamond.
 *   twMarkSVG({fill, stroke, strokeWidth, cls})  -> an <svg> string with <path class="tw-t|tw-w|tw-diamond">
 *   TW_PATHS.t / .w / .diamond                   -> the raw path data (for masks, clip-paths, strokes) */
(function (g) {
  var TW_PATHS = {
    t: "M0.00,87.50 C508.50,-35.42 491.50,-35.42 1000.00,87.50 L1000.00,285.00 C785.80,174.84 819.71,187.61 579.00,162.00 L579.00,431.00 L500.00,388.00 L421.00,431.00 L421.00,162.00 C180.29,187.61 214.20,174.84 0.00,285.00 Z",
    w: "M25.00,432.00 L147.00,358.00 C200.10,552.77 163.28,554.33 281.00,725.00 L500.00,501.00 L719.00,725.00 C836.72,554.33 799.90,552.77 853.00,358.00 L975.00,432.00 C916.43,706.60 925.26,688.52 769.00,931.00 C619.43,857.35 626.42,842.09 500.00,718.00 C373.58,842.09 380.57,857.35 231.00,931.00 C74.74,688.52 83.57,706.60 25.00,432.00 Z",
    diamond: "M500.00,877.00 L616.00,981.00 L500.00,1113.00 L384.00,981.00 Z"
  };
  function twMarkSVG(o) {
    o = o || {};
    var fill = o.fill || "currentColor", stroke = o.stroke || "none", sw = o.strokeWidth || 0, cls = o.cls || "";
    var attrs = ' fill="' + fill + '" stroke="' + stroke + '" stroke-width="' + sw + '" stroke-linejoin="round"';
    return '<svg class="tw-mark ' + cls + '" viewBox="0 0 1000 1114.1" xmlns="http://www.w3.org/2000/svg">' +
      '<path class="tw-t" d="' + TW_PATHS.t + '"' + attrs + '/>' +
      '<path class="tw-w" d="' + TW_PATHS.w + '"' + attrs + '/>' +
      '<path class="tw-diamond" d="' + TW_PATHS.diamond + '"' + attrs + '/></svg>';
  }
  g.TW_PATHS = TW_PATHS;
  g.twMarkSVG = twMarkSVG;
})(window);
