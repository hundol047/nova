"""Combine transport facts with documented official-boundary status. No clinical reasoning."""
from competition.schema import OFFICIAL_API_STATUS, SCHEMA_STATUS
from nova_agent.llm_preflight import PreflightStatus


def readiness_report(client):
    transport = client.last_preflight.as_dict()
    official = OFFICIAL_API_STATUS == "VERIFIED" and SCHEMA_STATUS == "CONFIRMED_OFFICIAL"
    status = transport["status"]
    if transport["runtime_ready"]:
        status = "READY" if official else "OFFICIAL_SCHEMA_UNVERIFIED"
    return {"status": status, "transport": transport, "official_api": OFFICIAL_API_STATUS,
            "official_schema": SCHEMA_STATUS, "official_submission_ready": official and transport["runtime_ready"],
            "model_weights_attested": False}
