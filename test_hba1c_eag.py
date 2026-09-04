"""Tests for the core HbA1c/eAG conversion functionality."""
import pytest
import hba1c_eag as m


class TestConvertHba1c:
    """Tests for the convert_hba1c function."""

    def test_from_hba1c_percent(self):
        """Standard HbA1c of 7.0% should yield known eAG values."""
        result = m.convert_hba1c(hba1c_percent=7.0)
        assert result["hba1c_percent"] == 7.0
        assert result["eag_mgdl"] == pytest.approx(154.2, abs=0.1)
        assert result["ifcc_mmol_mol"] == pytest.approx(53.0, abs=0.5)
        assert "eag_mmol" in result

    def test_from_eag_mgdl(self):
        """eAG of 154.2 mg/dL should round-trip to ~7.0%."""
        result = m.convert_hba1c(eag_mgdl=154.2)
        assert result["hba1c_percent"] == pytest.approx(7.0, abs=0.1)
        assert result["eag_mgdl"] == 154.2

    def test_from_ifcc(self):
        """IFCC of 53 mmol/mol should round-trip to ~7.0%."""
        result = m.convert_hba1c(ifcc_mmol=53.0)
        assert result["hba1c_percent"] == pytest.approx(7.0, abs=0.1)

    def test_low_hba1c(self):
        """Normal low HbA1c of 5.0%."""
        result = m.convert_hba1c(hba1c_percent=5.0)
        assert result["hba1c_percent"] == 5.0
        assert result["eag_mgdl"] == pytest.approx(96.8, abs=0.1)

    def test_high_hba1c(self):
        """High HbA1c of 10.0% (poorly controlled diabetes)."""
        result = m.convert_hba1c(hba1c_percent=10.0)
        assert result["hba1c_percent"] == 10.0
        assert result["eag_mgdl"] == pytest.approx(240.3, abs=0.1)

    def test_no_arguments_raises(self):
        """Calling with no arguments should raise ConversionError."""
        with pytest.raises(m.ConversionError, match="Provide one of"):
            m.convert_hba1c()

    def test_multiple_arguments_raises(self):
        """Providing more than one argument should raise ConversionError."""
        with pytest.raises(m.ConversionError, match="only one"):
            m.convert_hba1c(hba1c_percent=7.0, eag_mgdl=154.2)

    def test_invalid_input_type(self):
        """Non-numeric input should raise ConversionError."""
        with pytest.raises(m.ConversionError):
            m.convert_hba1c(hba1c_percent="not_a_number")

    def test_out_of_range_hba1c(self):
        """HbA1c outside physiological bounds should raise ConversionError."""
        with pytest.raises(m.ConversionError, match="must be between"):
            m.convert_hba1c(hba1c_percent=50.0)

    def test_out_of_range_eag(self):
        """eAG outside physiological bounds should raise ConversionError."""
        with pytest.raises(m.ConversionError, match="must be between"):
            m.convert_hba1c(eag_mgdl=5000.0)

    def test_nan_input(self):
        """NaN input should raise ConversionError."""
        with pytest.raises(m.ConversionError, match="finite"):
            m.convert_hba1c(hba1c_percent=float("nan"))

    def test_inf_input(self):
        """Infinity input should raise ConversionError."""
        with pytest.raises(m.ConversionError, match="finite"):
            m.convert_hba1c(hba1c_percent=float("inf"))

    def test_string_numeric_input(self):
        """String representation of a number should be accepted."""
        result = m.convert_hba1c(hba1c_percent="7.0")
        assert result["hba1c_percent"] == 7.0


class TestAssessRow:
    """Tests for the assess_row routing function."""

    def test_hba1c_routing(self):
        """Rows with hba1c_percent should route to convert_hba1c."""
        result = m.assess_row({"hba1c_percent": 7.0})
        assert "eag_mgdl" in result
        assert "error" not in result

    def test_eag_routing(self):
        """Rows with eag_mgdl should route to convert_hba1c."""
        result = m.assess_row({"eag_mgdl": 154.2})
        assert "hba1c_percent" in result
        assert "error" not in result

    def test_meld_na_routing(self):
        """Rows with bilirubin and creatinine should route to MELD-Na."""
        result = m.assess_row({
            "bilirubin": 1.5, "creatinine": 1.0, "inr": 1.2, "sodium": 135
        })
        # MELD-Na returns a float score directly
        assert isinstance(result, (int, float))

    def test_qtc_routing(self):
        """Rows with qt and hr_bpm should route to QTc calculator."""
        result = m.assess_row({"qt": 400, "hr_bpm": 70})
        # QTc returns a float directly
        assert isinstance(result, (int, float))

    def test_qtc_with_rr(self):
        """QTc from RR interval."""
        result = m.calculate_qtc(400, rr_ms=1000)
        assert isinstance(result, (int, float))
        assert result > 0

    def test_bmi_routing(self):
        """Rows with weight_kg should route to BMI calculator."""
        result = m.assess_row({"weight_kg": 70, "height_cm": 175, "age_months": 360})
        # BMI returns a float directly
        assert isinstance(result, (int, float))

    def test_generic_fallback(self):
        """Unknown row format should return a score dict."""
        result = m.assess_row({"value": 10})
        assert isinstance(result, dict)
        assert "score" in result

    def test_invalid_row_type(self):
        """Non-dict input should return an error dict."""
        result = m.assess_row("not a dict")
        assert "error" in result

    def test_empty_dict(self):
        """Empty dict should return a generic score of 0."""
        result = m.assess_row({})
        assert isinstance(result, dict)
        assert result.get("score") == 0.0


class TestCalculateScore:
    """Tests for the generic scoring fallback."""

    def test_numeric_inputs(self):
        result = m.calculate_score(a=10, b=20, c=30)
        assert result["score"] == 20.0
        assert result["min"] == 10
        assert result["max"] == 30

    def test_mixed_inputs(self):
        result = m.calculate_score(x=5.0, y="abc", z=15.0)
        assert result["score"] == 10.0
        assert "y" not in result["numeric_fields"]

    def test_no_numeric_inputs(self):
        result = m.calculate_score(name="test", label="example")
        assert result["score"] == 0.0


class TestProcessCsv:
    """Tests for CSV batch processing."""

    def test_process_sample_csv(self, tmp_path):
        """Process the sample CSV and verify output."""
        import shutil
        import os

        sample = os.path.join(os.path.dirname(__file__), "sample.csv")
        if not os.path.exists(sample):
            pytest.skip("sample.csv not found")

        output = str(tmp_path / "output.csv")
        results = m.process_csv(sample, output)
        assert len(results) == 2
        assert os.path.exists(output)

        # Verify output has the expected fields
        import csv
        with open(output, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert "eag_mgdl" in rows[0]
            assert "ifcc_mmol_mol" in rows[0]

    def test_missing_input_file(self):
        """Processing a non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            m.process_csv("/nonexistent/path/file.csv", "/tmp/out.csv")
