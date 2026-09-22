"""Standalone clinical data models (spec section 17).

nova_agent previously imported Allergy/Medication/VitalSigns from the vendored SynexAgent backend
(backend/app/schemas.py). That made a competition submission of nova_agent alone impossible
without also shipping backend/ -- these are the same fields, defined natively here instead, so
nova_agent has zero required dependency on backend/. (Optional reuse of backend's AuditStore /
vitals.assess / terminology_mapper still happens through nova_agent/_synex.py when backend/ is
present, but nothing in PatientState requires it any more.)
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Medication(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    status: Literal["active", "stopped", "unknown"] = "active"
    note: str = Field(default="", max_length=500)


class Allergy(BaseModel):
    substance: str = Field(min_length=1, max_length=200)
    category: Literal["medication", "food", "environment", "unknown"] = "unknown"
    severity: Literal["NONE", "MILD", "MODERATE", "SEVERE", "UNKNOWN"] = "UNKNOWN"
    reaction: str = Field(default="", max_length=500)


class VitalSigns(BaseModel):
    sbp: Optional[int] = Field(default=None, ge=40, le=300)
    dbp: Optional[int] = Field(default=None, ge=20, le=200)
    heart_rate: Optional[int] = Field(default=None, ge=20, le=250)
    respiratory_rate: Optional[int] = Field(default=None, ge=4, le=60)
    temperature_c: Optional[float] = Field(default=None, ge=25, le=45)
    spo2: Optional[int] = Field(default=None, ge=0, le=100)
    raw_text: str = ""
