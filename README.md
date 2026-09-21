# nova

nova 공모전 — N.O.V.A. 2026 대화형 의료 진단 AI 에이전트 대회 참가 프로젝트.

This repository contains two things:

- **N.O.V.A. Doctor Agent** (`nova_agent/`, `competition/`, `evaluation/`, `tests/`) — the
  conversational diagnosis agent built for the competition. Start here: **[README_NOVA.md](README_NOVA.md)**.
- **SynexAgent** (`backend/`, `frontend/`, `docs/`, ...) — the existing medical decision-support
  system (medication risk/interaction checking, EMR/FHIR clinical workspace) this agent reuses
  patient-data schemas, audit logging, vitals, and terminology-mapping code from. Its own
  documentation: **[README_SYNEXAGENT.md](README_SYNEXAGENT.md)**.

The Doctor Agent is fully independent of SynexAgent's React/Vite UI and FastAPI server — it never
needs them running to operate (see README_NOVA.md's Installation / Local execution sections).
