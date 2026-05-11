import pytest

from core.plugin.interfaces import AgentPlugin, ToolPlugin
from core.plugin.registry import PluginRegistry


class _MockTool:
    name = "mock_tool"

    def invoke(self, args):
        return "result"


class _MockToolPlugin(ToolPlugin):
    name = "mock_tool_plugin"

    def get_tools(self) -> list:
        return [_MockTool()]


class _MockAgentPlugin(AgentPlugin):
    name = "mock_agent"

    def build_graph(self, llm, tools, checkpointer=None):
        return None


def test_register_agent_no_tools():
    registry = PluginRegistry()
    registry.register_agent(_MockAgentPlugin())
    assert "mock_agent" in registry.agent_names
    assert registry.get_tools("mock_agent") == []


def test_register_agent_with_tools():
    registry = PluginRegistry()
    registry.register_agent(_MockAgentPlugin(), tool_plugins=[_MockToolPlugin()])
    tools = registry.get_tools("mock_agent")
    assert len(tools) == 1
    assert tools[0].name == "mock_tool"


def test_get_agent_unknown_raises():
    registry = PluginRegistry()
    with pytest.raises(KeyError, match="no_such_agent"):
        registry.get_agent("no_such_agent")


def test_agent_names_returns_all():
    registry = PluginRegistry()
    registry.register_agent(_MockAgentPlugin())
    assert registry.agent_names == ["mock_agent"]


def test_shutdown_calls_agent_shutdown():
    shutdown_called = []

    class _TrackingAgent(_MockAgentPlugin):
        def shutdown(self):
            shutdown_called.append(True)

    registry = PluginRegistry()
    registry.register_agent(_TrackingAgent())
    registry.shutdown()
    assert shutdown_called == [True]
