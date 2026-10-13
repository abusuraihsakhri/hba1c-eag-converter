/* Small dependency-free interface; results never leave this page. */
(function () {
  'use strict';
  const form = document.getElementById('converter-form');
  const source = document.getElementById('source');
  const value = document.getElementById('value');
  const error = document.getElementById('error');
  const result = document.getElementById('results');
  const copy = document.getElementById('copy');
  const download = document.getElementById('download');
  const units = {
    hba1c_percent: 'HbA1c (%)',
    eag_mgdl: 'eAG (mg/dL)',
    eag_mmol: 'eAG (mmol/L)',
    ifcc_mmol_mol: 'HbA1c (mmol/mol IFCC)'
  };
  let latest = null;

  function update() {
    const raw = value.value.trim();
    latest = null;
    error.textContent = '';
    result.hidden = true;
    copy.disabled = true;
    download.disabled = true;
    value.removeAttribute('aria-invalid');
    if (raw === '') {
      error.textContent = 'Enter a measurement.';
      value.setAttribute('aria-invalid', 'true');
      return;
    }
    try {
      const converted = window.HbA1cConverter.convert(Number(raw), source.value);
      for (const key of Object.keys(units)) {
        document.getElementById('out-' + key).textContent = converted[key];
      }
      latest = converted;
      result.hidden = false;
      copy.disabled = false;
      download.disabled = false;
    } catch (exception) {
      error.textContent = exception.message;
      value.setAttribute('aria-invalid', 'true');
    }
  }

  function format() {
    return Object.keys(units).map(function (key) {
      return units[key] + ': ' + latest[key];
    }).join('\n');
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    update();
  });
  source.addEventListener('change', function () {
    const examples = {
      hba1c_percent: 7, eag_mgdl: 154.2, eag_mmol: 8.6, ifcc_mmol: 53
    };
    const bounds = window.HbA1cConverter.BOUNDS[source.value];
    value.min = bounds[0];
    value.max = bounds[1];
    value.value = examples[source.value];
    update();
  });
  value.addEventListener('input', update);

  copy.addEventListener('click', async function () {
    if (!latest) return;
    try {
      await navigator.clipboard.writeText(format());
      copy.textContent = 'Copied';
    } catch (_error) {
      copy.textContent = 'Clipboard unavailable';
    }
  });
  download.addEventListener('click', function () {
    if (!latest) return;
    const keys = Object.keys(units);
    const csv = keys.join(',') + '\n' + keys.map(function (key) {
      return latest[key];
    }).join(',') + '\n';
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'hba1c-eag-conversion.csv';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  });
  update();
}());
