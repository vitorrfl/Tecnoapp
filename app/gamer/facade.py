from __future__ import annotations

from .engine import GamerEngine
from .tweaks import cpu, gpu, network, system


def build_engine() -> GamerEngine:
    """Return a GamerEngine pre-loaded with all registered tweaks."""
    engine = GamerEngine()
    cpu.register_all(engine)
    gpu.register_all(engine)
    system.register_all(engine)
    network.register_all(engine)
    return engine
