# N.O.V.A. Production Architecture (Backend-Integrated)

This document covers the **backend-integrated** N.O.V.A. production path: `nova_agent/` wrapped by
`backend/app/services/nova_service.py` and exposed through this repo's existing SynexAgent FastAPI
app (`backend/app/main.py`). It does not cover `docs/ARCHITECTURE.md`/`docs/SECURITY.md`/etc,
which belong to the pre-existing SynexAgent risk-model/rule-engine feature this backend already
had, nor the OTHER production path this project also has -- see "Two production paths" below.

## Pipeline

```
Hospital EMR / FHIR
        |
FastAPI Production API (backend/app/main.py, existing SynexAgent app)
        |
FHIR/EMR normalization (backend/app/services/nova_fhir_mapper.py)
        |
N.O.V.A. ClinicalPresentation (nova_agent/clinical_presentation.py)
        |
CandidateGenerator (nova_agent/candidate_generator.py)
        |
DoctorAgent (nova_agent/orchestrator.py)
        |
Differential / Safety / ActionSelector (nova_agent/differential.py, safety.py, action_selector.py)
        |
Clinician-facing Recommendation (backend/app/nova_schemas.py: NovaDecideResponse)
        |
Audit + Persistence (backend/app/services/audit.py [reused], nova_repository.py)
```

## Two production paths

This project has **two** independent production surfaces, built in different rounds, for different
integration needs:

| | `production/` (standalone) | `backend/` (this document) |
|---|---|---|
| Auth | Its own API-key + RBAC (`production/auth.py`) | Reuses this backend's existing OIDC/session auth (`backend/app/services/auth.py`) |
| FHIR/EMR | None | Real FHIR/EMR integration (`emr_adapter.py`, `nova_fhir_mapper.py`) |
| Audit | Its own in-memory `AuditRepository` | Reuses the existing SQLite `AuditStore` |
| Dependencies | FastAPI + uvicorn only, isolated from `backend/` | Already-installed backend deps; zero new ones |
| Intended use | A minimal, self-contained decision-support API with no hospital-system dependency | A deployment that already runs (or will run) this SynexAgent backend against a real hospital FHIR/OIDC/SMART stack |

Neither depends on the other. `nova_agent/` is the single shared reasoning engine both wrap,
unmodified either way. Pick `backend/` when the deployment target is (or will become) a real
hospital EMR/OIDC integration -- that is what this round of work was built for. `production/`
remains available for a lighter-weight, hospital-infrastructure-independent deployment.

## Backend components

```
backend/app/
  main.py                       existing SynexAgent app; POST/GET /v1/nova/* added here
  nova_schemas.py                request/response Pydantic models for /v1/nova/*
  services/
    nova_service.py              NovaService -- the ONLY code that touches nova_agent internals
    nova_fhir_mapper.py           Patient/ClinicalEncounter -> PatientState (read-only, one direction)
    nova_repository.py            NovaCaseRepository (in-memory; see Remaining blockers)
    nova_observability.py         structured logging + in-process metrics
    production_guard.py           NOVA_ENV=production startup validation
    auth.py                       UNCHANGED except for 3 new permissions (nova:read/invoke/review)
    audit.py                      UNCHANGED, reused as-is (case_id plays the role patient_id normally does)
    idempotency.py                UNCHANGED, available for future HTTP-level Idempotency-Key reuse
```

### `NovaService`

Wraps `nova_agent.orchestrator.DoctorAgent` (never `competition/adapter.py` -- that implements the
competition PROTOCOL, unrelated to a production HTTP API). A fresh `DoctorAgent` (and LLM client)
is constructed per `decide()`/`add_observation()` call, avoiding a real concurrency race in
`BaseLLMClient`'s per-call instance attributes (the same fix this project's earlier standalone
`production/api.py` needed, and needs here too since orchestrator.py itself is shared and unchanged).

```python
class NovaService:
    def create_case(self, *, adapter, patient_id, encounter, chief_complaint, created_by, max_turns=None): ...
    def add_observation(self, case_id, *, observation_id, action_type, key, result): ...
    def decide(self, case_id) -> DecideResult: ...
    def get_case(self, case_id): ...
    def close_case(self, case_id, *, reason=""): ...
```

### FHIR/EMR normalization

`nova_fhir_mapper.apply_patient_context(state, patient, encounter)` populates a freshly-created
`PatientState` with everything already known in the EMR at case-creation time: `conditions` ->
`past_medical_history`, active `medications` -> both `state.medications` (structured) and
`medication_text` (raw-fact preservation, since a drug catalog id alone doesn't always carry the
class/indication context `nova_agent`'s risk-factor matching needs), `allergies` -> `state.allergies`
(direct field-for-field mapping -- backend's `Allergy` and `nova_agent.models.Allergy` happen to
share the same field names), `labs` -> `laboratory_tests`, and the encounter's latest `VitalSigns`
-> `state.vital_signs` (backend's `VitalSigns` and `nova_agent.models.VitalSigns` also share field
names: `sbp`/`dbp`/`heart_rate`/`respiratory_rate`/`temperature_c`/`spo2`).

Read-only, one direction only. No code path here or anywhere in `backend/app/services/nova_service.py`
writes back to `app.state.adapter` or a real FHIR server.

## Clinical safety boundary

Every response from `POST /v1/nova/cases/{id}/decide` and `GET /v1/nova/cases/{id}` carries
`clinician_review_required: true` (fixed, never a toggle) and a safety banner
(`nova_service.CLINICAL_SAFETY_BANNER`). No `/v1/nova/*` endpoint calls
`app.state.medication_order_repo`/`app.state.lab_order_repo` -- N.O.V.A. never places, modifies,
or cancels a real clinical order. See `docs/NOVA_CLINICAL_SAFETY.md`.

## `ClinicalAgent` vs. `NovaService` -- roles stay separate

`backend/app/services/clinical_agent.py`'s `ClinicalAgent` (deterministic rule-engine + ONNX risk
model, medication/interaction-focused) and `NovaService`+`DoctorAgent` (interactive diagnostic
decision support) are deliberately never merged into one score. `/agent/analyze` and
`/v1/nova/cases/.../decide` are separate endpoints returning separate, independently-interpretable
results -- a future UI may show both side by side, but nothing in this backend combines a NOVA
differential confidence and a SynexAgent risk probability into a single number.
