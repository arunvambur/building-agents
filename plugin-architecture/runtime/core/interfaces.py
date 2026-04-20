class AgentPlugin:
    name: str

    def build_graph(self, llm):
        """Return compiled LangGraph agent"""
        raise NotImplementedError

class RouterPlugin:
    def route(self, state) -> str:
        """Return agent name"""
        raise NotImplementedError
    
class ToolPlugin:
    name: str

    def get_tools(self):
        """Return list of LangChain tools"""
        return []
    