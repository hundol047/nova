# N.O.V.A. 2026 Browser Clinical Reasoning Workspace

A standalone Streamlit app for **development, manual testing, demo, and clinical reasoning
visualization** -- NOT the competition submission interface (that is `submission/run.py`) and NOT
a rename of the separate SynexAgent hospital workspace (`frontend/`). It uses the SAME clinical
reasoning core every other entry point uses (`nova_agent.orchestrator.DoctorAgent`), through the
thin `nova_web_adapter.py` translation layer -- there is only one clinical reasoning engine.

```
Browser UI (nova_app.py)
    |
NovaWebSession (nova_web_adapter.py)
    |
nova_agent.orchestrator.DoctorAgent   <-- the ONE clinical reasoning core
```

## Run it

```bash
pip install -r requirements-web.txt
python -m streamlit run web/nova_app.py
```

Then open **http://localhost:8501**.

### Windows (PowerShell) example

```powershell
cd C:\path\to\nova
py -m pip install -r requirements-web.txt
$env:NOVA_LLM_PROVIDER = "mock"
py -m streamlit run web\nova_app.py
```

Expected: `http://localhost:8501`.

Do NOT use `npm run dev` to reach this workspace -- that launches the separate SynexAgent
Clinical Workspace frontend (`frontend/`), not N.O.V.A.

## Environment variables

| Variable | Effect |
|---|---|
| `NOVA_LLM_PROVIDER` | `mock` (default, offline/deterministic), `anthropic`, `openai_compatible`, `local`, `competition` -- same values `nova_agent/config.py` reads everywhere else. `mock` shows a mandatory "DEVELOPMENT MODE - MOCK LLM - NOT A REAL LLM" banner in the sidebar; any other provider shows real success/failure/fallback call counts instead. |
| `NOVA_WEB_DEBUG=1` | Shows an extra debug panel (retained differential/LLM counters/turn data) for development. Off by default -- the default UI never exposes internal scoring. |

## What it is / is not

- **Is**: a manual-testing chat-style interface over `DoctorAgent` -- start a case, answer
  ASK/EXAM/TEST prompts N.O.V.A. itself selects, see the differential/must-not-miss/turn-budget
  state the agent already tracks, reach a DIAGNOSE.
- **Is not**: a second reasoning engine, a replacement for `submission/run.py` (the actual
  competition entry point), or part of the competition protocol.
- **Never** included in `submission/` -- `scripts/build_nova_submission.py` only ever copies
  `nova_agent/` and `competition/`; it has no reference to `web/` at all.
- **Never** displays internal ranking scores as calibrated clinical probabilities -- the sidebar
  differential panel explicitly labels them "ranking score", matching `nova_agent`'s own
  `confidence_band` semantics (LOW/MEDIUM/HIGH), never a percentage.

## Session behavior

- Reusing the SAME `DoctorAgent`/`PatientState` pair across every Streamlit rerun (stored in
  `st.session_state`, never reconstructed on a widget interaction) is what makes turn history,
  the differential, and LLM call counters persist correctly across the whole case.
- **New Patient / Reset Case** clears that session state entirely -- the next case gets a fresh
  `DoctorAgent`/`PatientState`, never any leftover data from the previous patient.
- A `decide()`/`observe()` failure is caught and shown as a plain error message, never a raw
  Python stack trace (unless `NOVA_WEB_DEBUG=1`).

## Files

- `nova_web_adapter.py` -- the adapter (`NovaWebSession`): translates between Streamlit-friendly
  plain data and `DoctorAgent`/`PatientState`. No reasoning logic lives here.
- `nova_app.py` -- the Streamlit page itself (intake form, chat-style turn loop, sidebar status
  panels, i18n text table for English/Korean).
