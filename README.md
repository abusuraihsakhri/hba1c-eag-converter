# HbA1c ↔ eAG Converter

Convert HbA1c (NGSP/DCCT %), IFCC HbA1c (mmol/mol), and estimated average glucose (eAG in mg/dL or mmol/L). The browser calculator runs locally without a server or external JavaScript dependencies. A Python conversion API, command line tool, and legacy prototype audit endpoints are also available.

## Browser calculator

Open [web/index.html](web/index.html) in a modern browser, or run a local static server:

```bash
python -m http.server 8080 --directory web
```

Open `http://localhost:8080/`. Select a measurement, enter a value, and view all four converted values. Copy results or export a single conversion as CSV. Browser calculations use no network requests, cookies, analytics, or storage; external reference links open only when selected. Do not enter patient identifiers.

The browser implementation uses JavaScript directly because the conversion equations do not require a Python interpreter or Pyodide.

## Equations

- **ADAG:** `eAG (mg/dL) = 28.7 × HbA1c (%) − 46.7`
- **Glucose units:** `eAG (mmol/L) = eAG (mg/dL) / 18.015`
- **IFCC/NGSP:** `IFCC (mmol/mol) ≈ 10.929 × (HbA1c (%) − 2.15)`

Inverse conversions rearrange the same equations. Values are rounded for display. Inputs are validated against the tool's configured computational ranges, **not** clinical reference intervals or diagnostic thresholds.

At HbA1c 7.0%, the converter reports eAG **154.2 mg/dL**, **8.6 mmol/L**, and IFCC HbA1c **53.0 mmol/mol**.

Sources: [American Diabetes Association ADAG calculator](https://professional.diabetes.org/es/node/171) and [NGSP IFCC standardization](https://ngsp.org/ifcc.asp).

**Clinical limitation:** eAG is a population-regression estimate, not a directly measured mean glucose, and may differ substantially from an individual's glucose measurements. HbA1c can also be unreliable with altered erythrocyte survival or some assay interferences. This tool does not diagnose or recommend treatment.

## Python CLI and batch processing

Python 3.10 or newer is required.

```bash
python -m pip install -e .
hba1c-eag single --hba1c 7
hba1c-eag single --ifcc 53
hba1c-eag single --eag 154.2
hba1c-eag single --eag-mmol 8.6
hba1c-eag batch --input sample.csv --output results.csv
```

A direct `python hba1c_eag.py ...` invocation also works. The Python API is:

```python
from hba1c_eag import convert_hba1c
result = convert_hba1c(hba1c_percent=7)
```

For batch input, provide a CSV header with one populated measurement per row: `hba1c_percent`, `eag_mgdl`, `eag_mmol`, or `ifcc_mmol`. Empty cells are ignored. Input columns are retained and conversion fields or error messages are added.

The module also contains historical ancillary calculators, including MELD-Na (2016), QTc, BMI (not a BMI z-score), and APRI/FIB-4. They are separate from the HbA1c converter, are not clinical decision support, and should be independently validated before use.

## Local API and audit prototype

The optional FastAPI application serves the calculator from a source checkout and exposes stateless `POST /api/convert`:

```bash
python -m pip install -e .
hba1c-eag-audit serve --host 127.0.0.1 --port 8000
curl -s -X POST http://127.0.0.1:8000/api/convert \
  -H 'Content-Type: application/json' \
  -d '{"hba1c_percent":7}'
```

The OpenAPI schema is at `/openapi.json`; interactive API documentation is at `/docs`. The legacy audit, chat, and simulation code is a **prototype** with generic threshold rules and deterministic mock responses, not validated clinical safety infrastructure.

The audit trail is kept **in memory**, uses HMAC-SHA256, and is lost on restart. Set `AUDIT_SECRET_KEY` in the environment if stable signing keys are needed across process runs. Retrieving `GET /api/audit/logs` additionally requires `AUDIT_LOGS_TOKEN` and the `Authorization: Bearer <token>` header; without a configured token, log retrieval is disabled. The regex identifier filter cannot guarantee de-identification. **Do not submit real protected health information to the audit API.**

Docker and Compose configurations provide an optional local API deployment; they do not enable a backend on GitHub Pages.

## Development and tests

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q agents cli.py hba1c_eag.py
node --test tests/test_browser_converter.cjs
```

The browser site targets current Chrome, Firefox, Safari, and Edge versions. Python tests run on versions 3.10–3.13 in GitHub Actions, alongside browser-logic tests and a dependency vulnerability scan.

## License

[MIT](LICENSE).
