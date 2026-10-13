"""Regression coverage for calculation and audit defects."""
import csv
import json

import pytest

from agents.base import AuditTrail
from hba1c_eag import (
    assess_row, calculate_apri_fib4, calculate_meld_na, convert_hba1c,
    main, process_csv, ConversionError,
)


def test_ifcc_and_mmol_routing():
    assert assess_row({"ifcc_mmol": "53"})["hba1c_percent"] == 7.0
    assert assess_row({"eag_mmol": "8.6"})["hba1c_percent"] == pytest.approx(7.03)
    assert convert_hba1c(eag_mmol=8.6)["eag_mgdl"] == 154.9


def test_empty_batch_cells_are_ignored(tmp_path):
    source = tmp_path / "inputs.csv"
    result = tmp_path / "result.csv"
    source.write_text(
        "hba1c_percent,eag_mgdl,ifcc_mmol\n7,,\n,154.2,\n,,53\n", encoding="utf-8"
    )
    rows = process_csv(str(source), str(result))
    assert len(rows) == 3
    assert [r["hba1c_percent"] for r in rows] == ["7.0", "7.0", "7.0"]
    with result.open(encoding="utf-8", newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 3


def test_scalar_score_csv_output(tmp_path):
    source, output = tmp_path / "input.csv", tmp_path / "output.csv"
    source.write_text("qt_ms,rr_ms\n400,1000\n", encoding="utf-8")
    process_csv(str(source), str(output))
    with output.open(encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["result"] == "0.4"


def test_cli_from_ifcc(capsys):
    assert main(["single", "--ifcc", "53"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["hba1c_percent"] == 7.0


def test_cli_invalid_args(capsys):
    assert main(["single"]) == 2
    assert main(["single", "--json", "{invalid"]) == 2
    assert main(["single", "--hba1c", "90"]) == 2
    assert "must be between" in capsys.readouterr().err


def test_meld_na_legacy_coefficient_and_dialysis():
    assert calculate_meld_na(1, 1, 1, 137, False) == 6
    assert calculate_meld_na(1, 1, 1, 137, True) > 6
    assert calculate_meld_na(1.5, 1, 1.2, 135, False) == 10.0


def test_apri_and_fib4_platelet_units():
    scores = calculate_apri_fib4(80, 50, 200, 50)
    assert scores["apri"] == 1.0
    assert scores["fib4"] == pytest.approx(2.828, abs=0.002)


def test_integrity_detects_tampering():
    log = AuditTrail("test-only-key")
    log.log("worker", "test", "created", {"count": 1})
    log.log("worker", "test", "updated", {"count": 2})
    assert log.verify_integrity()
    copies = log.get_trail()
    copies[0]["actor"] = "changed"
    assert log.verify_integrity()
    log.logs[0]["payload_hash"] = "f" * 64
    assert not log.verify_integrity()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_bad_input(value):
    with pytest.raises(ConversionError):
        convert_hba1c(eag_mmol=value)
