__all__ = ["EvacuationAgent"]


def __getattr__(name: str):
    if name == "EvacuationAgent":
        from app.agent.planner import EvacuationAgent
        return EvacuationAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
