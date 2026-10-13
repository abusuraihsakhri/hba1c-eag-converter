/* ADAG and IFCC/NGSP conversion equations. No network requests or storage. */
(function (root) {
  'use strict';

  const FACTOR = 18.015;
  const BOUNDS = {
    hba1c_percent: [2, 25],
    eag_mgdl: [10, 600],
    eag_mmol: [10 / FACTOR, 600 / FACTOR],
    ifcc_mmol: [0, 250]
  };

  function convert(input, unit) {
    if (!Object.prototype.hasOwnProperty.call(BOUNDS, unit)) {
      throw new RangeError('Select a supported input unit.');
    }
    if (typeof input !== 'number' || !Number.isFinite(input)) {
      throw new RangeError('Enter a finite numeric value.');
    }
    const bounds = BOUNDS[unit];
    if (input < bounds[0] || input > bounds[1]) {
      throw new RangeError('Enter a value between ' +
        (Math.round(bounds[0] * 100) / 100) + ' and ' +
        (Math.round(bounds[1] * 100) / 100) + '.');
    }

    const a1c = unit === 'hba1c_percent' ? input
      : unit === 'ifcc_mmol' ? input / 10.929 + 2.15
      : ((unit === 'eag_mmol' ? input * FACTOR : input) + 46.7) / 28.7;
    const glucose = 28.7 * a1c - 46.7;
    const ifcc = 10.929 * (a1c - 2.15);
    function round(value, places) {
      return Number(value.toFixed(places));
    }
    return {
      hba1c_percent: round(a1c, 2),
      eag_mgdl: round(glucose, 1),
      eag_mmol: round(glucose / FACTOR, 1),
      ifcc_mmol_mol: round(ifcc, 1)
    };
  }

  const api = { convert: convert, BOUNDS: BOUNDS };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  root.HbA1cConverter = api;
}(typeof window !== 'undefined' ? window : globalThis));
