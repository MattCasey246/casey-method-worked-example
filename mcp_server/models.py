"""Typed models shared by the MCP server, dashboard backend and (later) the guarded agent.

Same housing/Awaab domain as dataset.jsonl so the whole demo tells one story.
"""
from typing import Literal, Optional
from pydantic import BaseModel

Priority = Literal["Emergency", "Urgent", "Routine"]
RepairStatus = Literal["open", "scheduled", "closed"]
Vulnerability = Literal["child", "elderly", "respiratory", "none"]

# Damp-risk score at or above this fires the Awaab serious-hazard alert.
DAMP_ALERT_THRESHOLD = 70


class Property(BaseModel):
    id: str
    address: str
    build_type: str
    occupant_vulnerability: Vulnerability


class Repair(BaseModel):
    id: str
    property_id: str
    description: str
    reported_at: str  # ISO date
    status: RepairStatus
    priority: Priority
    hazard_flag: bool


class SensorReading(BaseModel):
    property_id: str
    timestamp: str  # ISO datetime
    temp_c: float
    humidity_pct: float
    co2_ppm: int
    damp_risk_score: int  # 0-100


class RepairSummary(BaseModel):
    """Slim shape returned by list_repairs (detail via get_repair)."""
    id: str
    property_id: str
    priority: Priority
    status: RepairStatus
    hazard_flag: bool
    description: str
