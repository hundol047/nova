"""Private evaluation cases must be independent: nothing patient-derived from case A may influence case B.

Every sequence below runs on ONE shared NovaCompetitionAgent (as the organizer runtime may) and must
reproduce exactly the transcript each case produces on a fresh agent."""
import copy

import pytest

from competition.adapter import NovaCompetitionAgent
from evaluation.cases import CASES
from evaluation.preliminary_dev_cases import PRELIM_KO_CASES
from evaluation.preliminary_driver import run_episode, run_interleaved
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent

_BY_ID = {c.case_id: c for c in PRELIM_KO_CASES}
A = _BY_ID["PrelimKo_ChestPain_GERD"]
B = _BY_ID["PrelimKo_Fever_URI"]
C = CASES[0]  # English tuning case with a different language/domain


def fresh():
    return NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()), preliminary=True)


def sig(ep):
    return [(w["action_type"], w["content"], (w.get("metadata") or {}).get("key")) for w in ep.wire]


@pytest.fixture(scope="module")
def solo():
    return {c.case_id: sig(run_episode(c, agent=fresh())) for c in (A, B, C)}


def test_a_then_b_equals_b_alone(solo):
    agent = fresh()
    run_episode(A, agent=agent)
    assert sig(run_episode(B, agent=agent)) == solo[B.case_id]


def test_b_then_a_equals_a_alone(solo):
    agent = fresh()
    run_episode(B, agent=agent)
    assert sig(run_episode(A, agent=agent)) == solo[A.case_id]


def test_a_b_a_repeats_exactly(solo):
    agent = fresh()
    first = sig(run_episode(A, agent=agent))
    run_episode(B, agent=agent)
    assert sig(run_episode(A, agent=agent)) == first == solo[A.case_id]


def test_cross_language_neighbour_does_not_leak_locale(solo):
    agent = fresh()
    run_episode(A, agent=agent)  # Korean first
    english = run_episode(C, agent=agent)
    assert sig(english) == solo[C.case_id]
    assert not any(any("가" <= ch <= "힣" for ch in w["content"]) for w in english.wire)


def test_interleaved_cases_share_nothing(solo):
    agent = fresh()
    ea, eb = run_interleaved([A, B], agent)
    assert sig(ea) == solo[A.case_id] and sig(eb) == solo[B.case_id]
    assert not agent._states and not agent._pending_actions and not agent._emitted_actions and not agent._closing_done


def test_same_case_id_reused_after_cleanup(solo):
    agent = fresh()
    run_episode(A, agent=agent)
    clone = copy.deepcopy(B)
    clone.case_id = A.case_id  # a different patient behind a reused id
    assert [s[:2] for s in sig(run_episode(clone, agent=agent))] == [s[:2] for s in solo[B.case_id]]


def test_patient_text_of_a_never_appears_in_b():
    agent = fresh()
    run_episode(A, agent=agent)
    eb = run_episode(B, agent=agent)
    soap = eb.wire[-1]["soap"]
    blob = "\n".join(soap.values())
    for marker in ("제산제", "신물", "커피", "이영희"):
        assert marker not in blob


def test_exception_during_a_does_not_poison_b(solo):
    agent = fresh()
    obs = {"case_id": "X", "observation_type": "initial", "chief_complaint": "가슴이 아파요. 50세 남자",
           "demographics": {"age": 50, "sex": "male"}}
    agent.act(obs)
    with pytest.raises(Exception):
        agent.act({"case_id": "X", "observation_type": "say_response", "content": 12345, "bogus": object()})
    assert "X" not in agent._states  # state dropped on error, no tombstone
    assert sig(run_episode(B, agent=agent)) == solo[B.case_id]


def test_failed_llm_during_a_does_not_change_b(solo):
    class Explodes(MockLLMClient):
        calls = 0

        def generate_turn_output(self, ctx):
            Explodes.calls += 1
            raise TimeoutError("simulated timeout")

    agent = NovaCompetitionAgent(agent=DoctorAgent(llm_client=Explodes()), preliminary=True)
    ep_a = run_episode(A, agent=agent)
    assert ep_a.wire[-1]["action_type"] == "DIAGNOSE"          # timeout during A still ends in a diagnosis
    agent.agent.llm_client = MockLLMClient()                   # transport recovers
    assert sig(run_episode(B, agent=agent)) == solo[B.case_id]


def test_llm_telemetry_is_per_case_not_cumulative():
    agent = fresh()
    ea = run_episode(A, agent=agent)
    eb = run_episode(B, agent=agent)
    assert eb.result["llm_calls"] is not None
    assert eb.result["llm_calls"] <= ea.result["llm_calls"] + 8  # not A's count plus its own


def _cached_functions():
    import importlib
    import inspect
    import pkgutil
    import nova_agent
    out = []
    for info in pkgutil.walk_packages(nova_agent.__path__, "nova_agent."):
        try:
            module = importlib.import_module(info.name)
        except Exception:  # noqa: BLE001 - optional modules
            continue
        for name, obj in vars(module).items():
            if (hasattr(obj, "cache_info") and hasattr(obj, "__wrapped__")
                    and getattr(obj.__wrapped__, "__module__", "").startswith("nova_agent")):
                out.append((f"{info.name}.{name}", obj, inspect.signature(obj.__wrapped__)))
    return out


def test_every_process_wide_cache_is_a_static_zero_argument_loader():
    """A cache keyed by arguments could hold patient text; only argument-free (static knowledge) loaders may exist."""
    cached = _cached_functions()
    assert cached, "expected to discover the static knowledge caches"
    for name, fn, signature in cached:
        assert len(signature.parameters) == 0, f"{name} caches by argument -> could retain patient-derived data"


def test_running_a_patient_case_does_not_grow_static_caches_or_lay_tables():
    import nova_agent.matching as matching
    before_lay = set(matching._LAY_VARIANTS)
    run_episode(A, agent=fresh())  # warm every static cache once
    sizes = {n: fn.cache_info().currsize for n, fn, _ in _cached_functions()}
    run_episode(B, agent=fresh())
    assert {n: fn.cache_info().currsize for n, fn, _ in _cached_functions()} == sizes
    assert set(matching._LAY_VARIANTS) == before_lay
