"""
QC Crypto Lab — FastAPI app, port 8002.
Endpoints: /auth/*, /scenarios/*, /runs/*, /approaches/*, /reports/*, /dashboard
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

import database as db
from database import Approach, RefreshToken, Scenario, ScenarioRun, SessionLocal, User
from auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    require_admin,
    revoke_refresh_token,
    validate_refresh_token,
    verify_password,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_LAB_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="QC Crypto Lab API",
    version="1.0.0",
    description="Quantum Cryptography Lab — 42 demo scenarios, runs, approaches, reports",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3030",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def _startup():
    db.init_db()
    db.seed_scenarios()
    logger.info("QC Crypto Lab API started — DB initialised and seeded.")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ApproachUpdate(BaseModel):
    hld_title: Optional[str] = None
    hld_overview: Optional[str] = None
    hld_components: Optional[str] = None
    hld_diagram_nodes: Optional[str] = None
    hld_diagram_edges: Optional[str] = None
    lld_title: Optional[str] = None
    lld_details: Optional[str] = None
    lld_modules: Optional[str] = None
    protocol_layers: Optional[str] = None
    security_flow: Optional[str] = None
    report_summary: Optional[str] = None
    report_metrics: Optional[str] = None
    report_findings: Optional[str] = None


class RunRequest(BaseModel):
    input_params: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_dict(u: User) -> Dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def _scenario_dict(s: Scenario) -> Dict[str, Any]:
    return {
        "id": s.id,
        "module": s.module,
        "module_name": s.module_name,
        "title": s.title,
        "demo_pitch": s.demo_pitch,
        "status": s.status,
        "file_path": s.file_path,
        "priority": s.priority,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _run_dict(r: ScenarioRun) -> Dict[str, Any]:
    return {
        "id": r.id,
        "scenario_id": r.scenario_id,
        "status": r.status,
        "input_params": _safe_json(r.input_params),
        "output": _safe_json(r.output),
        "duration_ms": r.duration_ms,
        "ran_at": r.ran_at.isoformat() if r.ran_at else None,
    }


def _approach_dict(a: Approach) -> Dict[str, Any]:
    return {
        "id": a.id,
        "scenario_id": a.scenario_id,
        "approach_type": a.approach_type,
        "hld_title": a.hld_title,
        "hld_overview": a.hld_overview,
        "hld_components": _safe_json(a.hld_components),
        "hld_diagram_nodes": _safe_json(a.hld_diagram_nodes),
        "hld_diagram_edges": _safe_json(a.hld_diagram_edges),
        "lld_title": a.lld_title,
        "lld_details": a.lld_details,
        "lld_modules": _safe_json(a.lld_modules),
        "protocol_layers": _safe_json(a.protocol_layers),
        "security_flow": _safe_json(a.security_flow),
        "report_summary": a.report_summary,
        "report_metrics": _safe_json(a.report_metrics),
        "report_findings": _safe_json(a.report_findings),
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _safe_json(val: Optional[str]) -> Any:
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception:
        return val


def _get_scenario_or_404(session, scenario_id: str) -> Scenario:
    s = session.get(Scenario, scenario_id)
    if s is None:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
    return s


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/register", tags=["Auth"])
def register(body: RegisterRequest):
    session = SessionLocal()
    try:
        existing = session.query(User).filter_by(email=body.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            id=str(uuid.uuid4()),
            email=body.email,
            hashed_password=hash_password(body.password),
            full_name=body.full_name,
            role="viewer",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        access = create_access_token(user.id, user.email, user.role)
        refresh = create_refresh_token(user.id)

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "user": _user_dict(user),
        }
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        logger.error("register error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        session.close()


@app.post("/auth/login", tags=["Auth"])
def login(body: LoginRequest):
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(email=body.email).first()
        if user is None or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account deactivated")

        access = create_access_token(user.id, user.email, user.role)
        refresh = create_refresh_token(user.id)

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "user": _user_dict(user),
        }
    except HTTPException:
        raise
    finally:
        session.close()


@app.post("/auth/refresh", tags=["Auth"])
def refresh_token(body: RefreshRequest):
    payload = validate_refresh_token(body.refresh_token)
    user_id: str = payload["sub"]

    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or deactivated")

        new_access = create_access_token(user.id, user.email, user.role)
        return {"access_token": new_access, "token_type": "bearer"}
    finally:
        session.close()


@app.post("/auth/logout", tags=["Auth"])
def logout(body: LogoutRequest):
    try:
        payload = validate_refresh_token(body.refresh_token)
        jti = payload.get("jti", "")
        revoke_refresh_token(jti)
    except HTTPException:
        pass  # Already invalid — treat as logged out
    return {"message": "Logged out"}


@app.get("/auth/me", tags=["Auth"])
def me(current_user: User = Depends(get_current_user)):
    return _user_dict(current_user)


# ---------------------------------------------------------------------------
# Scenarios endpoints
# ---------------------------------------------------------------------------

@app.get("/scenarios/summary", tags=["Scenarios"])
def scenarios_summary():
    """Counts by module, status, priority."""
    session = SessionLocal()
    try:
        all_s = session.query(Scenario).all()
        by_module: Dict[int, Dict[str, Any]] = {}
        by_status: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}

        for s in all_s:
            m = s.module
            if m not in by_module:
                by_module[m] = {"module": m, "module_name": s.module_name, "total": 0,
                                 "implemented": 0, "partial": 0, "pending": 0}
            by_module[m]["total"] += 1
            by_module[m][s.status] = by_module[m].get(s.status, 0) + 1

            by_status[s.status] = by_status.get(s.status, 0) + 1
            by_priority[s.priority] = by_priority.get(s.priority, 0) + 1

        return {
            "total": len(all_s),
            "by_module": list(by_module.values()),
            "by_status": by_status,
            "by_priority": by_priority,
        }
    finally:
        session.close()


@app.get("/scenarios", tags=["Scenarios"])
def list_scenarios(
    module: Optional[int] = Query(None, description="Filter by module number 1-5"),
    status: Optional[str] = Query(None, description="Filter by status: implemented/partial/pending"),
    priority: Optional[str] = Query(None, description="Filter by priority: P0/P1/P2"),
):
    session = SessionLocal()
    try:
        q = session.query(Scenario)
        if module is not None:
            q = q.filter(Scenario.module == module)
        if status is not None:
            q = q.filter(Scenario.status == status)
        if priority is not None:
            q = q.filter(Scenario.priority == priority)
        scenarios = q.order_by(Scenario.module, Scenario.id).all()
        return [_scenario_dict(s) for s in scenarios]
    finally:
        session.close()


@app.get("/scenarios/{scenario_id}", tags=["Scenarios"])
def get_scenario(scenario_id: str):
    session = SessionLocal()
    try:
        s = _get_scenario_or_404(session, scenario_id)
        return _scenario_dict(s)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Runs endpoints
# ---------------------------------------------------------------------------

@app.post("/scenarios/{scenario_id}/run", tags=["Runs"])
def run_scenario(
    scenario_id: str,
    body: RunRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute the scenario's Python file as a subprocess, capture stdout, store result."""
    session = SessionLocal()
    try:
        s = _get_scenario_or_404(session, scenario_id)

        # Create a run record (status=running)
        run = ScenarioRun(
            scenario_id=scenario_id,
            status="running",
            input_params=json.dumps(body.input_params),
            output="{}",
            duration_ms=0,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    finally:
        session.close()

    # Resolve file path relative to lab dir
    file_path = s.file_path
    if file_path.startswith("../../"):
        abs_path = str(_LAB_DIR.parent / file_path[6:])
    else:
        abs_path = str(_LAB_DIR / file_path)

    t0 = time.time()
    stdout_text = ""
    stderr_text = ""
    exit_code = -1

    try:
        result = subprocess.run(
            [sys.executable, abs_path],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_LAB_DIR),
        )
        stdout_text = result.stdout[:4000]
        stderr_text = result.stderr[:2000]
        exit_code = result.returncode
        final_status = "completed" if exit_code == 0 else "failed"
    except FileNotFoundError:
        stderr_text = f"File not found: {abs_path}"
        final_status = "failed"
    except subprocess.TimeoutExpired:
        stderr_text = "Execution timed out after 120s"
        final_status = "failed"
    except Exception as exc:
        stderr_text = str(exc)
        final_status = "failed"

    duration_ms = int((time.time() - t0) * 1000)
    output = json.dumps({
        "stdout": stdout_text,
        "stderr": stderr_text,
        "exit_code": exit_code,
        "file_path": abs_path,
    })

    # Update run record
    session2 = SessionLocal()
    try:
        run_obj = session2.get(ScenarioRun, run_id)
        if run_obj:
            run_obj.status = final_status
            run_obj.output = output
            run_obj.duration_ms = duration_ms
            session2.commit()
            session2.refresh(run_obj)
            return _run_dict(run_obj)
        return {"id": run_id, "status": final_status, "duration_ms": duration_ms}
    finally:
        session2.close()


@app.get("/scenarios/{scenario_id}/runs", tags=["Runs"])
def get_scenario_runs(scenario_id: str):
    session = SessionLocal()
    try:
        _get_scenario_or_404(session, scenario_id)
        runs = (
            session.query(ScenarioRun)
            .filter_by(scenario_id=scenario_id)
            .order_by(ScenarioRun.ran_at.desc())
            .limit(50)
            .all()
        )
        return [_run_dict(r) for r in runs]
    finally:
        session.close()


@app.get("/runs", tags=["Runs"])
def list_all_runs(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    session = SessionLocal()
    try:
        q = session.query(ScenarioRun)
        if status:
            q = q.filter(ScenarioRun.status == status)
        total = q.count()
        runs = q.order_by(ScenarioRun.ran_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "runs": [_run_dict(r) for r in runs],
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Approaches (AS-IS / TO-BE) endpoints
# ---------------------------------------------------------------------------

@app.get("/scenarios/{scenario_id}/approaches", tags=["Approaches"])
def get_approaches(scenario_id: str):
    session = SessionLocal()
    try:
        _get_scenario_or_404(session, scenario_id)
        approaches = session.query(Approach).filter_by(scenario_id=scenario_id).all()
        return [_approach_dict(a) for a in approaches]
    finally:
        session.close()


@app.get("/scenarios/{scenario_id}/approaches/{approach_type}", tags=["Approaches"])
def get_approach(scenario_id: str, approach_type: str):
    if approach_type not in ("classical", "quantum"):
        raise HTTPException(status_code=400, detail="approach_type must be 'classical' or 'quantum'")
    session = SessionLocal()
    try:
        _get_scenario_or_404(session, scenario_id)
        a = session.query(Approach).filter_by(
            scenario_id=scenario_id, approach_type=approach_type
        ).first()
        if a is None:
            raise HTTPException(status_code=404, detail=f"No {approach_type} approach for {scenario_id}")
        return _approach_dict(a)
    finally:
        session.close()


@app.put("/scenarios/{scenario_id}/approaches/{approach_type}", tags=["Approaches"])
def update_approach(
    scenario_id: str,
    approach_type: str,
    body: ApproachUpdate,
    _admin: User = Depends(require_admin),
):
    if approach_type not in ("classical", "quantum"):
        raise HTTPException(status_code=400, detail="approach_type must be 'classical' or 'quantum'")
    session = SessionLocal()
    try:
        _get_scenario_or_404(session, scenario_id)
        a = session.query(Approach).filter_by(
            scenario_id=scenario_id, approach_type=approach_type
        ).first()
        if a is None:
            raise HTTPException(status_code=404, detail=f"No {approach_type} approach for {scenario_id}")

        update_data = body.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(a, field, value)

        session.commit()
        session.refresh(a)
        return _approach_dict(a)
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Reports endpoints
# ---------------------------------------------------------------------------

@app.get("/scenarios/{scenario_id}/report", tags=["Reports"])
def get_scenario_report(scenario_id: str):
    """Combined AS-IS (classical) + TO-BE (quantum) report for a scenario."""
    session = SessionLocal()
    try:
        s = _get_scenario_or_404(session, scenario_id)
        approaches = session.query(Approach).filter_by(scenario_id=scenario_id).all()
        app_by_type = {a.approach_type: _approach_dict(a) for a in approaches}

        # Latest run
        latest_run = (
            session.query(ScenarioRun)
            .filter_by(scenario_id=scenario_id)
            .order_by(ScenarioRun.ran_at.desc())
            .first()
        )

        return {
            "scenario": _scenario_dict(s),
            "classical_approach": app_by_type.get("classical"),
            "quantum_approach": app_by_type.get("quantum"),
            "latest_run": _run_dict(latest_run) if latest_run else None,
            "generated_at": _now(),
        }
    finally:
        session.close()


@app.get("/reports/summary", tags=["Reports"])
def reports_summary():
    """All scenarios with their approach summaries."""
    session = SessionLocal()
    try:
        scenarios = session.query(Scenario).order_by(Scenario.module, Scenario.id).all()
        result = []
        for s in scenarios:
            approaches = session.query(Approach).filter_by(scenario_id=s.id).all()
            app_summaries = {
                a.approach_type: {
                    "hld_title": a.hld_title,
                    "report_summary": a.report_summary,
                    "report_metrics": _safe_json(a.report_metrics),
                }
                for a in approaches
            }
            result.append({
                "scenario": _scenario_dict(s),
                "approaches": app_summaries,
            })
        return {"total": len(result), "reports": result}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Dashboard endpoint
# ---------------------------------------------------------------------------

@app.get("/dashboard", tags=["Dashboard"])
def dashboard():
    """Aggregate stats for the lab dashboard."""
    session = SessionLocal()
    try:
        all_scenarios = session.query(Scenario).all()
        total = len(all_scenarios)
        implemented = sum(1 for s in all_scenarios if s.status == "implemented")
        partial = sum(1 for s in all_scenarios if s.status == "partial")
        pending = sum(1 for s in all_scenarios if s.status == "pending")

        # Module breakdown
        module_counts: Dict[int, Dict[str, Any]] = {}
        for s in all_scenarios:
            m = s.module
            if m not in module_counts:
                module_counts[m] = {
                    "module": m,
                    "module_name": s.module_name,
                    "total": 0,
                    "implemented": 0,
                    "partial": 0,
                    "pending": 0,
                    "p0": 0,
                }
            module_counts[m]["total"] += 1
            module_counts[m][s.status] = module_counts[m].get(s.status, 0) + 1
            if s.priority == "P0":
                module_counts[m]["p0"] += 1

        # Priority breakdown
        p0 = sum(1 for s in all_scenarios if s.priority == "P0")
        p1 = sum(1 for s in all_scenarios if s.priority == "P1")
        p2 = sum(1 for s in all_scenarios if s.priority == "P2")

        # Recent runs
        recent_runs = (
            session.query(ScenarioRun)
            .order_by(ScenarioRun.ran_at.desc())
            .limit(10)
            .all()
        )

        # Top scenarios by run count
        from sqlalchemy import func
        top_by_runs = (
            session.query(ScenarioRun.scenario_id, func.count(ScenarioRun.id).label("run_count"))
            .group_by(ScenarioRun.scenario_id)
            .order_by(func.count(ScenarioRun.id).desc())
            .limit(5)
            .all()
        )

        total_runs = session.query(ScenarioRun).count()
        completed_runs = session.query(ScenarioRun).filter_by(status="completed").count()
        failed_runs = session.query(ScenarioRun).filter_by(status="failed").count()

        return {
            "total_scenarios": total,
            "implemented_pct": round(implemented / total * 100, 1) if total else 0,
            "status_breakdown": {
                "implemented": implemented,
                "partial": partial,
                "pending": pending,
            },
            "priority_breakdown": {"P0": p0, "P1": p1, "P2": p2},
            "module_breakdown": list(module_counts.values()),
            "total_runs": total_runs,
            "runs_breakdown": {
                "completed": completed_runs,
                "failed": failed_runs,
                "success_rate_pct": round(completed_runs / total_runs * 100, 1) if total_runs else 0,
            },
            "recent_runs": [_run_dict(r) for r in recent_runs],
            "top_scenarios_by_runs": [
                {"scenario_id": row.scenario_id, "run_count": row.run_count}
                for row in top_by_runs
            ],
            "generated_at": _now(),
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "qc-crypto-lab-api", "port": 8002}
