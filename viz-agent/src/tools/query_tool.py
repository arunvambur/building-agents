from core.plugin.interfaces import ToolPlugin


class QueryTools(ToolPlugin):
    """
    Tool plugin for the data_agent.
    Provides tools for querying and filtering structured data sources.
    """

    name = "query_tools"

    def get_tools(self) -> list:
        # TODO: register LangChain @tool functions here, e.g.:
        # from tools.query_functions import fetch_dataset, filter_records
        # return [fetch_dataset, filter_records]
        return []
