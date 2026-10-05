from langgraph.checkpoint.base import BaseCheckpointSaver

from agent.silo_agent import SiloAgent


class ObjectsFactory:
    """Creates and holds the application objects. init() runs once at server start."""

    _agent: SiloAgent | None = None

    @classmethod
    def init(cls, checkpointer: BaseCheckpointSaver) -> None:
        cls._agent = SiloAgent(checkpointer)

    @classmethod
    def get_agent(cls) -> SiloAgent:
        """FastAPI dependency: returns the agent built at startup."""
        if cls._agent is None:
            raise RuntimeError("ObjectsFactory.init() was not called.")
        return cls._agent
