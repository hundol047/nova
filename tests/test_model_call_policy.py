"""Model-call efficiency: compact prompts, a narrow active differential, and the INTERNAL call budget."""
from competition.adapter import NovaCompetitionAgent
from evaluation.preliminary_dev_cases import PRELIM_KO_CASES
from evaluation.preliminary_driver import run_episode
from nova_agent.config import PRELIMINARY_MAX_LLM_CALLS_PER_CASE, get_config
from nova_agent.llm_client import MockLLMClient, _deterministic_turn_output, build_reasoning_prompt
from nova_agent.orchestrator import DoctorAgent

CASES = {c.case_id: c for c in PRELIM_KO_CASES}


class Recording(MockLLMClient):
    """Behaves like a REAL client for accounting (flags set) but answers deterministically and offline."""

    def __init__(self):
        self.prompts, self.turns = [], []

    def generate_turn_output(self, ctx):
        self.prompts.append(build_reasoning_prompt(ctx))
        self.turns.append(len(ctx.differential))
        self._last_call_was_real = True
        self._last_call_succeeded = True
        return _deterministic_turn_output(ctx)


def _run(case_id):
    client = Recording()
    agent = NovaCompetitionAgent(agent=DoctorAgent(llm_client=client), preliminary=True)
    ep = run_episode(CASES[case_id], agent=agent)
    return client, ep


def test_calls_stay_inside_the_internal_budget_and_include_first_and_final_turn():
    client, ep = _run("PrelimKo_ChestPain_ACS")
    assert 1 <= len(client.prompts) <= PRELIMINARY_MAX_LLM_CALLS_PER_CASE
    assert ep.result["llm_calls"] == len(client.prompts)
    assert ep.wire[-1]["action_type"] == "DIAGNOSE"


def test_prompt_is_compact_and_never_dumps_the_catalog():
    client, _ = _run("PrelimKo_Dyspnea_PE")
    longest = max(len(p) for p in client.prompts)
    assert longest < 16_000, f"prompt grew to {longest} characters"
    from nova_agent.knowledge.retrieval import all_diseases
    names = [d["name"] for d in all_diseases().values()]
    assert sum(1 for p in client.prompts[-1:] for n in names if n in p) <= 3 * get_config().top_k_differential


def test_active_differential_is_narrow():
    client, _ = _run("PrelimKo_Headache_SAH")
    assert max(client.turns) <= get_config().reasoning_top_k


def test_budget_is_labelled_internal_not_official():
    import nova_agent.config as config
    source = open(config.__file__, encoding="utf-8").read()
    assert "INTERNAL ENGINEERING BUDGET" in source
