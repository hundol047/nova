"""N.O.V.A. Doctor Agent - independent clinical reasoning module.

This package is self-contained and does not depend on any UI layer.
It can be driven directly (see nova_agent.orchestrator.DoctorAgent) or
through the competition adapter in competition/adapter.py.
"""

from nova_agent.orchestrator import DoctorAgent

__all__ = ["DoctorAgent"]
