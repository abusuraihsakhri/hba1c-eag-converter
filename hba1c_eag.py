#!/usr/bin/env python3
"""
HbA1c to eAG Converter
Bidirectional HbA1c (%) <-> eAG (mg/dL, mmol/L) via ADAG with IFCC mmol/mol.
Stdlib only.
"""
import argparse
import csv
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional

# Physiological bounds for validation
HBA1C_MIN = 2.0
HBA1C_MAX = 25.0
EAG_MGDL_MIN = 10.0
EAG_MGDL_MAX = 600.0
IFCC_MMIN = 0.0
IFCC_MAX = 250.0


class ConversionError(ValueError):
    """Raised when a conversion input is outside physiological bounds or otherwise invalid."""
    pass


def _validate_numeric(value: Any, name: str) -> float:
    """Validate and convert a numeric input."""
    if value is None:
        raise ConversionError(f"{name} cannot be None")
    try:
        result = float(value)
    except (TypeError, ValueError) as e:
        raise ConversionError(f"{name} must be a valid number, got {value!r}: {e}")
    if math.isnan(result) or math.isinf(result):
        raise ConversionError(f"{name} must be finite, got {result}")
    return result


def convert_hba1c(hba1c_percent: Optional[float] = None,
                  eag_mgdl: Optional[float] = None,
                  ifcc_mmol: Optional[float] = None) -> Dict[str, float]:
    """
    ADAG: eAG(mg/dL) = 28.7 * HbA1c - 46.7
    IFCC = 10.929 * (HbA1c - 2.15)
    Bidirectional conversion between HbA1c, eAG, and IFCC.

    Exactly one of hba1c_percent, eag_mgdl, or ifcc_mmol must be provided.
    """
    provided = sum(x is not None for x in [hba1c_percent, eag_mgdl, ifcc_mmol])
    if provided == 0:
        raise ConversionError("Provide one of hba1c_percent, eag_mgdl, ifcc_mmol")
    if provided > 1:
        raise ConversionError("Provide only one of hba1c_percent, eag_mgdl, ifcc_mmol")

    if hba1c_percent is not None:
        a1c = _validate_numeric(hba1c_percent, "hba1c_percent")
        if not (HBA1C_MIN <= a1c <= HBA1C_MAX):
            raise ConversionError(
                f"hba1c_percent must be between {HBA1C_MIN} and {HBA1C_MAX}, got {a1c}"
            )
        eag = 28.7 * a1c - 46.7
        ifcc = 10.929 * (a1c - 2.15)
        return {
            "hba1c_percent": round(a1c, 2),
            "eag_mgdl": round(eag, 1),
            "eag_mmol": round(eag / 18.015, 1),
            "ifcc_mmol_mol": round(ifcc, 1),
        }

    if eag_mgdl is not None:
        eag = _validate_numeric(eag_mgdl, "eag_mgdl")
        if not (EAG_MGDL_MIN <= eag <= EAG_MGDL_MAX):
            raise ConversionError(
                f"eag_mgdl must be between {EAG_MGDL_MIN} and {EAG_MGDL_MAX}, got {eag}"
            )
        a1c = (eag + 46.7) / 28.7
        ifcc = 10.929 * (a1c - 2.15)
        return {
            "hba1c_percent": round(a1c, 2),
            "eag_mgdl": round(eag, 1),
            "eag_mmol": round(eag / 18.015, 1),
            "ifcc_mmol_mol": round(ifcc, 1),
        }

    if ifcc_mmol is not None:
        ifcc = _validate_numeric(ifcc_mmol, "ifcc_mmol")
        if not (IFCC_MMIN <= ifcc <= IFCC_MAX):
            raise ConversionError(
                f"ifcc_mmol must be between {IFCC_MMIN} and {IFCC_MAX}, got {ifcc}"
            )
        a1c = ifcc / 10.929 + 2.15
        eag = 28.7 * a1c - 46.7
        return {
            "hba1c_percent": round(a1c, 2),
            "eag_mgdl": round(eag, 1),
            "eag_mmol": round(eag / 18.015, 1),
            "ifcc_mmol_mol": round(ifcc, 1),
        }

    raise ConversionError("Provide one of hba1c_percent, eag_mgdl, ifcc_mmol")


def calculate_score(**kwargs: Any) -> Dict[str, Any]:
    """
    Generic scoring fallback for unrecognized row formats.
    Returns the input values with basic statistical summary.
    """
    numeric_vals: Dict[str, float] = {}
    for k, v in kwargs.items():
        try:
            numeric_vals[k] = float(v)
        except (TypeError, ValueError):
            continue

    if not numeric_vals:
        return {"input_keys": list(kwargs.keys()), "score": 0.0}

    values = list(numeric_vals.values())
    return {
        "input_keys": list(kwargs.keys()),
        "numeric_fields": numeric_vals,
        "score": round(sum(values) / len(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def calculate_meld_na(bilirubin: Any, creatinine: Any, inr: Any, sodium: Any,
                      dialysis: bool, albumin: Any = None, sex: str = "M") -> float:
    """Calculate MELD-Na score for liver disease severity."""
    try:
        bili = max(1.0, float(bilirubin))
        creat = min(max(1.0, float(creatinine)), 4.0)
        inr_val = max(1.0, float(inr))
        na = min(max(125.0, float(sodium)), 137.0)
    except (TypeError, ValueError) as e:
        raise ConversionError(f"Invalid MELD-Na input: {e}")

    meld = (
        0.957 * math.log(creat)
        + 0.378 * math.log(bili)
        + 1.120 * math.log(inr_val)
        + 0.643
    )
    meld_na = meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
    if dialysis:
        meld_na = max(meld_na, 40.0)
    return round(min(meld_na, 40.0), 1)


def calculate_qtc(qt_ms: Any, rr_ms: Any = None, hr_bpm: Any = None) -> float:
    """Calculate QTc from QT and RR interval or heart rate."""
    try:
        qt = float(qt_ms)
    except (TypeError, ValueError) as e:
        raise ConversionError(f"Invalid QT input: {e}")

    if rr_ms is not None:
        try:
            rr = float(rr_ms) / 1000.0
        except (TypeError, ValueError) as e:
            raise ConversionError(f"Invalid RR input: {e}")
    elif hr_bpm is not None:
        try:
            hr = float(hr_bpm)
            if hr <= 0:
                raise ConversionError("Heart rate must be positive")
            rr = 60.0 / hr
        except (TypeError, ValueError) as e:
            raise ConversionError(f"Invalid heart rate input: {e}")
    else:
        raise ConversionError("Either rr_ms or hr_bpm must be provided")

    if rr <= 0:
        raise ConversionError("RR interval must be positive")
    qtc = qt / 1000.0 / math.sqrt(rr)
    return round(qtc, 3)


def calculate_bmi_z(weight_kg: Any, height_cm: Any, age_months: Any, sex: str = "M") -> float:
    """Calculate BMI from weight and height."""
    try:
        wt = float(weight_kg)
        ht = float(height_cm) / 100.0
        float(age_months)
    except (TypeError, ValueError) as e:
        raise ConversionError(f"Invalid BMI input: {e}")

    if ht <= 0:
        raise ConversionError("Height must be positive")
    if wt <= 0:
        raise ConversionError("Weight must be positive")

    bmi = wt / (ht * ht)
    return round(bmi, 2)


def calculate_apri_fib4(ast_u_l: Any, alt_u_l: Any, platelets_109: Any, age_years: Any) -> Dict[str, float]:
    """Calculate APRI and FIB-4 scores for liver fibrosis."""
    try:
        ast_val = float(ast_u_l)
        alt_val = float(alt_u_l)
        plt = float(platelets_109) * 100
        age = float(age_years)
    except (TypeError, ValueError) as e:
        raise ConversionError(f"Invalid APRI/FIB-4 input: {e}")

    if alt_val <= 0 or plt <= 0:
        raise ConversionError("ALT and platelets must be positive")

    ast_uln = 40.0
    apri = ((ast_val / ast_uln) / plt) * 100
    fib4 = (age * ast_val) / (plt * math.sqrt(alt_val))

    return {"apri": round(apri, 3), "fib4": round(fib4, 3)}


def assess_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Route a row dictionary to the appropriate calculator based on its keys."""
    try:
        if not isinstance(row, dict):
            return {"error": f"Expected dict, got {type(row).__name__}"}

        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(
                row.get("bilirubin"), row.get("creatinine"),
                row.get("inr"), row.get("sodium"),
                row.get("dialysis", "0") == "1",
                row.get("albumin"), row.get("sex", "M")
            )

        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(
                row.get("qt_ms") or row.get("qt"),
                row.get("rr_ms"),
                row.get("hr_bpm") or row.get("heart_rate")
            )

        if "weight_kg" in row:
            return calculate_bmi_z(
                row.get("weight_kg"), row.get("height_cm"),
                row.get("age_months") or row.get("age") or 60,
                row.get("sex", "M")
            )

        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(
                row.get("hba1c_percent"), row.get("eag_mgdl")
            )

        if "ast_u_l" in row:
            return calculate_apri_fib4(
                row.get("ast_u_l"), row.get("alt_u_l"),
                row.get("platelets_109"),
                row.get("age_years") or row.get("age")
            )

        return calculate_score(**row)
    except ConversionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def process_csv(inp: str, out: str) -> List[Dict[str, str]]:
    """Process a CSV file, applying assess_row to each record."""
    if not os.path.isfile(inp):
        raise FileNotFoundError(f"Input file not found: {inp}")

    with open(inp, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if not fieldnames:
        raise ConversionError("CSV file has no headers")

    results = []
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k, v in res.items()}}
        results.append(merged)

    all_keys: set = set()
    for rr in results:
        all_keys.update(rr.keys())
    extra = [k for k in sorted(all_keys) if k not in fieldnames]

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames) + extra)
        writer.writeheader()
        writer.writerows(results)

    return results


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    p = argparse.ArgumentParser(prog="hba1c_eag", description="HbA1c to eAG Converter")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("single", help="Single calculation")
    s.add_argument("--json", help='JSON of inputs e.g. {"hba1c_percent": 7.0}')
    s.add_argument("--bili", type=float)
    s.add_argument("--creat", type=float)
    s.add_argument("--inr", type=float)
    s.add_argument("--na", type=float)
    s.add_argument("--qt", type=float)
    s.add_argument("--rr", type=float)
    s.add_argument("--hr", type=float)
    s.add_argument("--hba1c", type=float, help="HbA1c value in percent (DCCT/NGSP)")
    s.add_argument("--eag", type=float, help="eAG value in mg/dL")
    s.add_argument("--ifcc", type=float, help="IFCC value in mmol/mol")

    b = sub.add_parser("batch", help="Batch CSV processing")
    b.add_argument("--input", required=True)
    b.add_argument("--output", required=True)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    p = build_parser()
    a = p.parse_args(argv)

    if a.cmd == "single":
        if a.json:
            row = json.loads(a.json)
        else:
            row = {k: getattr(a, k) for k in ["bili", "creat", "inr", "na", "qt", "rr", "hr"] if getattr(a, k, None) is not None}
            if getattr(a, "bili", None) is not None:
                row["bilirubin"] = a.bili
            if getattr(a, "creat", None) is not None:
                row["creatinine"] = a.creat
            if getattr(a, "inr", None) is not None:
                row["inr"] = a.inr
            if getattr(a, "na", None) is not None:
                row["sodium"] = a.na
            if getattr(a, "qt", None) is not None:
                row["qt_ms"] = a.qt
            if getattr(a, "rr", None) is not None:
                row["rr_ms"] = a.rr
            if getattr(a, "hr", None) is not None:
                row["hr_bpm"] = a.hr
            if getattr(a, "hba1c", None) is not None:
                row["hba1c_percent"] = a.hba1c
            if getattr(a, "eag", None) is not None:
                row["eag_mgdl"] = a.eag
            if getattr(a, "ifcc", None) is not None:
                row["ifcc_mmol"] = a.ifcc
        result = assess_row(row)
        print(json.dumps(result, indent=2))
        return 0

    if a.cmd == "batch":
        try:
            res = process_csv(a.input, a.output)
            print(f"Processed {len(res)} -> {a.output}")
            return 0
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error processing CSV: {e}", file=sys.stderr)
            return 1

    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
