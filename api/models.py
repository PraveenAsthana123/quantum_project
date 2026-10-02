from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


class ServiceCheck(BaseModel):
    name: str
    reachable: bool
    latency_ms: Optional[float]


class StatusResponse(BaseModel):
    ok: bool
    timestamp: str
    overall: str
    services: List[ServiceCheck]
    quantum_packages: List[str]


class ProjectMetric(BaseModel):
    name: str
    value: str
    unit: str


class ProjectSummary(BaseModel):
    id: str
    title: str
    subtitle: str
    status: str
    category: str
    tier: int
    qubits: int
    accentColor: str
    last_run: Optional[str]
    accuracy: Optional[float]
    metrics: List[ProjectMetric]


class RunRecord(BaseModel):
    run_id: str
    project_id: str
    timestamp: str
    status: str
    accuracy: Optional[float]
    duration_ms: Optional[int]
    output: Optional[str]


class ProjectDetail(BaseModel):
    id: str
    title: str
    subtitle: str
    description: str
    status: str
    category: str
    tier: int
    qubits: int
    accentColor: str
    inputFormat: str
    outputFormat: str
    algorithms: List[str]
    tools: List[str]
    last_run: Optional[str]
    accuracy: Optional[float]
    metrics: List[ProjectMetric]
    run_history: List[RunRecord]


class LayerSummary(BaseModel):
    id: str
    title: str
    layerNumber: int
    qgId: str
    accentColor: str
    status: str
    last_checked: Optional[str]


class GateRecord(BaseModel):
    gate_id: str
    layer_id: str
    timestamp: str
    result: str
    details: str


class LayerDetail(BaseModel):
    id: str
    title: str
    subtitle: str
    layerNumber: int
    qgId: str
    accentColor: str
    description: str
    inputSpec: str
    processSpec: str
    outputSpec: str
    tools: List[str]
    status: str
    last_checked: Optional[str]
    gate_history: List[GateRecord]


class TriggerRequest(BaseModel):
    project_id: str


class TriggerResponse(BaseModel):
    run_id: str
    project_id: str
    status: str
    message: str


class CircuitGate(BaseModel):
    gate: str
    qubits: List[int]
    params: Optional[List[float]] = None


class CircuitResponse(BaseModel):
    project_id: str
    n_qubits: int
    depth: int
    n_parameters: int
    gates: List[CircuitGate]
    description: str
