# HbA1c to eAG Converter

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Standards:** ADAG (A1C-Derived Average Glucose), IFCC

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)

</div>

---

## What It Does

Bidirectional medical conversion between HbA1c (%), estimated Average Glucose (eAG in mg/dL and mmol/L), and IFCC (mmol/mol). Supports batch CSV processing and clinical score calculations.

---

## Key Features

- **ADAG Formula**: eAG(mg/dL) = 28.7 × HbA1c(%) − 46.7
- **IFCC Conversion**: IFCC(mmol/mol) = 10.929 × (HbA1c − 2.15)
- **Bidirectional**: Convert from any one known value to the others
- **Input Validation**: Physiological bounds checking with clear error messages
- **Batch Processing**: Process CSV files with multiple patient records
- **Clinical Scoring**: MELD-Na, QTc, BMI, APRI/FIB-4 calculators

---

## Mathematical Formulas

```
ADAG (mg/dL): eAG = 28.7 * HbA1c(%) - 46.7
ADAG (mmol/L): eAG_mmol = eAG_mgdl / 18.015
IFCC: IFCC = 10.929 * (HbA1c(%) - 2.15)
```

---

## Installation

```bash
pip install -e .
# Or with development dependencies:
pip install -e ".[dev]"
```

---

## Usage

### Command Line

```bash
# Single HbA1c to eAG conversion
python hba1c_eag.py single --hba1c 7.0

# eAG to HbA1c
python hba1c_eag.py single --eag 154.2

# IFCC to HbA1c
python hba1c_eag.py single --ifcc 53.0

# JSON input
python hba1c_eag.py single --json '{"hba1c_percent": 7.0}'

# Batch CSV processing
python hba1c_eag.py batch --input sample.csv --output results.csv
```

### Python API

```python
import hba1c_eag

# Convert HbA1c to eAG and IFCC
result = hba1c_eag.convert_hba1c(hba1c_percent=7.0)
# Returns: {'hba1c_percent': 7.0, 'eag_mgdl': 154.2, 'eag_mmol': 8.6, 'ifcc_mmol_mol': 53.0}

# Convert eAG to HbA1c
result = hba1c_eag.convert_hba1c(eag_mgdl=154.2)

# Convert IFCC to HbA1c
result = hba1c_eag.convert_hba1c(ifcc_mmol=53.0)
```

### Input Schema

| Field | Description | Unit |
|:------|:------------|:-----|
| `hba1c_percent` | HbA1c value (DCCT/NGSP) | % |
| `eag_mgdl` | Estimated Average Glucose | mg/dL |
| `ifcc_mmol` | IFCC standardised value | mmol/mol |

---

## Testing

```bash
# Run all tests
pytest -v

# Run only core conversion tests
pytest test_hba1c_eag.py -v

# Run with short tracebacks
pytest -v --tb=short
```

---

## Security

- **Input Validation**: All numeric inputs validated against physiological bounds
- **No External Network Calls**: Core conversion is stdlib-only
- **Audit Trail**: HMAC-SHA256 tamper-evident logging in the agents module
- **Zero-PHI Guard**: Regex-based detection of PHI in outbound data

Set `AUDIT_SECRET_KEY` environment variable for persistent audit integrity in production:

```bash
export AUDIT_SECRET_KEY="your-secret-key-here"
```

---

## Project Structure

```
hba1c-eag-converter/
├── hba1c_eag.py          # Core conversion & CLI
├── cli.py                # Extended CLI with agents framework
├── enrichment.py         # Enrichment engine suite
├── simulator.py          # High-throughput testing simulator
├── sample.csv            # Sample input data
├── test_hba1c_eag.py     # Core conversion tests
├── tests/                # Full test suite
├── agents/               # Enterprise agent framework
│   ├── base.py           # Security, PHI guard, audit trail
│   ├── models.py         # Pydantic schemas
│   ├── supervisor.py     # Multi-agent orchestrator
│   ├── workers.py        # Specialized scoring workers
│   └── ...
├── web/                  # Operations dashboard
├── Dockerfile            # Container build
└── docker-compose.yml    # Container orchestration
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
