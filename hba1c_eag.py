#!/usr/bin/env python3
"""
HbA1c to eAG Converter
Bidirectional HbA1c (%) <-> eAG (mg/dL, mmol/L) via ADAG with IFCC mmol/mol.
Stdlib only.
"""
import argparse, csv, sys, math

def convert_hba1c(hba1c_percent=None, eag_mgdl=None, ifcc_mmol=None):
    """ADAG: eAG(mg/dL)=28.7*HbA1c-46.7, IFCC =10.929*(HbA1c-2.15). Bidirectional."""
    if hba1c_percent is not None:
        a1c=float(hba1c_percent); eag=28.7*a1c-46.7; ifcc=10.929*(a1c-2.15)
        return {"hba1c_percent": round(a1c,2), "eag_mgdl": round(eag,1), "eag_mmol": round(eag/18.015,1), "ifcc_mmol_mol": round(ifcc,1)}
    if eag_mgdl is not None:
        eag=float(eag_mgdl); a1c=(eag+46.7)/28.7; ifcc=10.929*(a1c-2.15)
        return {"hba1c_percent": round(a1c,2), "eag_mgdl": round(eag,1), "eag_mmol": round(eag/18.015,1), "ifcc_mmol_mol": round(ifcc,1)}
    if ifcc_mmol is not None:
        ifcc=float(ifcc_mmol); a1c=ifcc/10.929+2.15; eag=28.7*a1c-46.7
        return {"hba1c_percent": round(a1c,2), "eag_mgdl": round(eag,1), "eag_mmol": round(eag/18.015,1), "ifcc_mmol_mol": round(ifcc,1)}
    raise ValueError("Provide one of hba1c_percent, eag_mgdl, ifcc_mmol")


def assess_row(row):
    try:
        # try common lab keys
        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(row.get("bilirubin"), row.get("creatinine"), row.get("inr"), row.get("sodium"), row.get("dialysis","0")=="1", row.get("albumin"), row.get("sex","M"))
        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(row.get("qt_ms") or row.get("qt"), row.get("rr_ms"), row.get("hr_bpm") or row.get("heart_rate"))
        if "weight_kg" in row:
            return calculate_bmi_z(row.get("weight_kg"), row.get("height_cm"), row.get("age_months") or row.get("age") or 60, row.get("sex","M"))
        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(row.get("hba1c_percent"), row.get("eag_mgdl"))
        if "ast_u_l" in row:
            return calculate_apri_fib4(row.get("ast_u_l"), row.get("alt_u_l"), row.get("platelets_109"), row.get("age_years") or row.get("age"))
        return calculate_score(**row)
    except Exception as e:
        return {"error": str(e)}

def process_csv(inp, out):
    import csv
    with open(inp, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f); rows=list(r); fieldnames=r.fieldnames
    results=[]
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k,v in res.items()}}
        results.append(merged)
    # union fieldnames
    all_keys=set()
    for rr in results: all_keys.update(rr.keys())
    # keep original first
    extra = [k for k in all_keys if k not in fieldnames]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(fieldnames)+extra); w.writeheader(); w.writerows(results)
    return results

def build_parser():
    p=argparse.ArgumentParser(prog="hba1c_eag", description="HbA1c to eAG Converter")
    sub=p.add_subparsers(dest="cmd", required=True)
    s=sub.add_parser("single", help="single calculation")
    s.add_argument("--json", help='JSON of inputs e.g. bil')
    s.add_argument("--bili", type=float); s.add_argument("--creat", type=float); s.add_argument("--inr", type=float); s.add_argument("--na", type=float)
    s.add_argument("--qt", type=float); s.add_argument("--rr", type=float); s.add_argument("--hr", type=float)
    b=sub.add_parser("batch", help="batch csv"); b.add_argument("--input", required=True); b.add_argument("--output", required=True)
    return p

def main(argv=None):
    import json as _json
    p=build_parser(); a=p.parse_args(argv)
    if a.cmd=="single":
        if a.json:
            row=_json.loads(a.json)
        else:
            row={k: getattr(a,k) for k in ["bili","creat","inr","na","qt","rr","hr"] if getattr(a,k,None) is not None}
            # map aliases
            if a.bili is not None: row["bilirubin"]=a.bili
            if a.creat is not None: row["creatinine"]=a.creat
            if a.inr is not None: row["inr"]=a.inr
            if a.na is not None: row["sodium"]=a.na
            if a.qt is not None: row["qt_ms"]=a.qt
            if a.rr is not None: row["rr_ms"]=a.rr
            if a.hr is not None: row["hr_bpm"]=a.hr
        print(assess_row(row))
        return 0
    if a.cmd=="batch":
        res=process_csv(a.input, a.output); print(f"Processed {len(res)} -> {a.output}"); return 0
    p.print_help(); return 1

if __name__=="__main__":
    import sys; sys.exit(main())
