"""End-to-end FastAPI checks for the conversion route and UI."""
import pytest
from fastapi.testclient import TestClient
from agents.api import app

client = TestClient(app)


def test_browser_page_and_assets():
    response = client.get("/")
    assert response.status_code == 200
    assert "HbA1c" in response.text
    assert client.get("/converter.js").status_code == 200
    assert client.get("/app.js").status_code == 200


def test_conversion_api():
    response = client.post("/api/convert", json={"hba1c_percent": 7})
    assert response.status_code == 200
    assert response.json()["eag_mgdl"] == 154.2
    assert client.post("/api/convert", json={"ifcc_mmol": 53}).json()["hba1c_percent"] == 7
    assert client.post("/api/convert", json={"eag_mmol": 8.6}).json()["eag_mgdl"] == 154.9


def test_invalid_conversion_rejected():
    assert client.post("/api/convert", json={"hba1c_percent": 7, "eag_mgdl": 154}).status_code == 422
    assert client.post("/api/convert", json={"hba1c_percent": 99}).status_code == 422
    assert client.post("/api/convert", json={}).status_code == 422


def test_audit_log_authentication(monkeypatch):
    monkeypatch.delenv("AUDIT_LOGS_TOKEN", raising=False)
    assert client.get("/api/audit/logs").status_code == 403
    monkeypatch.setenv("AUDIT_LOGS_TOKEN", "integration-test-secret")
    assert client.get("/api/audit/logs").status_code == 403
    assert client.get("/api/audit/logs", headers={
        "Authorization": "Bearer integration-test-secret"
    }).status_code == 200


def test_nonfinite_agent_input():
    from pydantic import ValidationError
    from agents.models import SystemTaskPayload
    with pytest.raises(ValidationError):
        SystemTaskPayload(task_id="x", target_identifier="y", primary_metric=float("inf"))
