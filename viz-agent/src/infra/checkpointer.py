from langgraph.checkpoint.memory import InMemorySaver


def build_checkpointer() -> InMemorySaver:
    """
    Returns an in-memory checkpointer for LangGraph conversation state.
    For production use, replace with a persistent backend (e.g. SqliteSaver, RedisSaver).
    """
    return InMemorySaver()
