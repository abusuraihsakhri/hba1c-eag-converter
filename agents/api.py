"""
FastAPI REST API Server for Hba1C Eag Converter.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
import hmac
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor
from hba1c_eag import convert_hba1c, ConversionError

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="HbA1c to eAG Converter API",
    description="HbA1c conversion and optional prototype audit endpoints",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "hba1c-eag-converter", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs(authorization: Optional[str] = Header(default=None)):
    # Identifiers in the audit trail must not be exposed anonymously.
    token = os.getenv("AUDIT_LOGS_TOKEN")
    expected = "Bearer " + token if token else ""
    if not token or not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=403, detail="Audit logs require authorization")
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}


class ConversionRequest(BaseModel):
    hba1c_percent: Optional[float] = None
    eag_mgdl: Optional[float] = None
    eag_mmol: Optional[float] = None
    ifcc_mmol: Optional[float] = None


@app.post("/api/convert")
def api_convert(payload: ConversionRequest):
    """Stateless numerical conversion; no identifiers or results are stored."""
    try:
        return convert_hba1c(**payload.model_dump())
    except ConversionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# Serve the same self-contained browser interface when launched from a checkout.
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
if WEB_ROOT.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_ROOT), html=True), name="converter-ui")
