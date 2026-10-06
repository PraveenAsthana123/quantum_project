"""Control Tower API routes — executive PQC dashboard endpoints."""
from __future__ import annotations

import pathlib
import sys
from dataclasses import asdict
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

# Add control-tower/src to path so the module resolves correctly
_BASE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_BASE / "control-tower" / "src"))

from quantum_control_tower import QuantumControlTower

router = APIRouter(prefix="/api/v1/tower", tags=["control-tower"])

_tower = QuantumControlTower(data_dir=str(_BASE / "pqc-control-tower" / "data"))


# ─── Helper ───────────────────────────────────────────────────────────────────

def _dc(obj: Any) -> Any:
    """Recursively convert dataclasses (and lists of them) to plain dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, list):
        return [_dc(item) for item in obj]
    return obj


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    summary="Executive PQC migration summary",
    description=(
        "Returns top-level KPIs: overall PQC score, layer counts, HNDL risk, "
        "compliance score, monthly spend, and projected completion year."
    ),
)
def get_summary() -> Dict[str, Any]:
    """GET /api/v1/tower/summary — aggregate TowerMetrics across all 29 layers."""
    try:
        metrics = _tower.get_executive_summary()
        return {"status": "ok", "data": _dc(metrics)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/layers",
    summary="All 29 security layer statuses",
    description=(
        "Returns the full migration state for each of the 29 security layers: "
        "completion %, current algorithm, target algorithm, HNDL risk, open findings."
    ),
)
def get_layers() -> Dict[str, Any]:
    """GET /api/v1/tower/layers — full 29-layer matrix."""
    try:
        layers = _tower.get_layer_matrix()
        return {
            "status": "ok",
            "count": len(layers),
            "data": _dc(layers),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/hndl-risk",
    summary="Harvest Now Decrypt Later risk assessment",
    description=(
        "Calculates HNDL exposure score (0–100) per layer, identifies priority systems "
        "with highest data-lifetime risk, and returns recommended immediate actions."
    ),
)
def get_hndl_risk() -> Dict[str, Any]:
    """GET /api/v1/tower/hndl-risk — HNDL risk breakdown."""
    try:
        assessment = _tower.get_hndl_risk_assessment()
        return {"status": "ok", "data": assessment}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/threats",
    summary="Quantum threat intelligence feed",
    description=(
        "Returns 10 seeded 2026 threat intelligence items sorted by severity: "
        "quantum annealer attacks, HNDL campaigns, CVEs, regulatory updates."
    ),
)
def get_threats() -> Dict[str, Any]:
    """GET /api/v1/tower/threats — threat intelligence items."""
    try:
        threats = _tower.get_threat_intelligence()
        return {
            "status": "ok",
            "count": len(threats),
            "data": _dc(threats),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/compliance",
    summary="CNSA 2.0 / NIST / DORA / NIS2 compliance status",
    description=(
        "Returns compliance status mapped to five frameworks: CNSA 2.0, NIST SP 1800-38, "
        "DORA Article 30, EU NIS2, and CISA PQC guidance."
    ),
)
def get_compliance() -> Dict[str, Any]:
    """GET /api/v1/tower/compliance — compliance framework status."""
    try:
        compliance = _tower.get_compliance_status()
        return {"status": "ok", "data": compliance}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/vendors",
    summary="Vendor PQC readiness matrix",
    description=(
        "Returns PQC readiness for 10 major vendors (AWS, Azure, GCP, Palo Alto, Cisco, "
        "Fortinet, CrowdStrike, HashiCorp Vault, Okta, Cloudflare): status, completion %, "
        "supported algorithms, hybrid availability."
    ),
)
def get_vendors() -> Dict[str, Any]:
    """GET /api/v1/tower/vendors — vendor PQC readiness."""
    try:
        vendors = _tower.get_vendor_pqc_readiness()
        return {
            "status": "ok",
            "count": len(vendors),
            "data": vendors,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/trends",
    summary="Historical KPI trend data",
    description=(
        "Returns simulated historical trend for overall PQC score, HNDL risk, and "
        "compliance score over the past N days (default 30, max 365)."
    ),
)
def get_trends(
    days: int = Query(default=30, ge=7, le=365, description="Number of days of history to return"),
) -> Dict[str, Any]:
    """GET /api/v1/tower/trends?days=30 — KPI trend history."""
    try:
        trends = _tower.get_kpi_trends(days=days)
        return {
            "status": "ok",
            "days_requested": days,
            "points": len(trends),
            "data": trends,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/ciso-report",
    summary="Full CISO / board-ready PQC migration report",
    description=(
        "Generates a structured CISO report including executive headline, 5 prioritized "
        "critical actions (P0/P1/P2), a 90-day milestone plan, budget estimate, and "
        "projected risk reduction percentage."
    ),
)
def get_ciso_report() -> Dict[str, Any]:
    """GET /api/v1/tower/ciso-report — full executive PQC report."""
    try:
        report = _tower.generate_ciso_report()
        return {"status": "ok", "data": report}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
