class AgentPlugin:
    name: str

    def build_graph(self, llm):
        pass
    
    def initialize(self):
        pass

    def shutdown(self):
        pass

class RouterPlugin:
    def route(self, state) -> str:
        pass
    
class ToolPlugin:
    name: str

    def get_tools(self):
        """Return list of LangChain tools"""
        return []
    
    def initialize(self):
        pass

    def shutdown(self):
        pass

class GuardrailPlugin:
    def validate(self, state):
        pass
    