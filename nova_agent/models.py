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
    # Round W: infants breathe faster than adults -- NICE NG143 Table 1 treats RR > 60 as a red feature in under-5s --
    # so a measured 64/min is a real (abnormal) value, not a typo to be discarded.
    respiratory_rate: Optional[int] = Field(default=None, ge=4, le=120)
    temperature_c: Optional[float] = Field(default=None, ge=25, le=45)
    spo2: Optional[int] = Field(default=None, ge=0, le=100)
    # Derived, not a direct measurement: |systolic1 - systolic2| when vitals_parser.py detects TWO
    # distinct blood-pressure readings reported for opposite limbs in the same result text (e.g.
    # "BP 180/60 right arm, 130/50 left arm") -- a classic objective sign for aortic dissection
    # (and other vascular pathology), previously structurally invisible to the scoring engine
    # because the old single-BP-only parser only ever kept the first reading. None means "no
    # bilateral reading reported", never "no differential" (that would be 0, a real finding).
    sbp_arm_differential: Optional[int] = Field(default=None, ge=0, le=200)
    raw_text: str = ""
