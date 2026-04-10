from langgraph.graph import StateGraph, END
from models import ResearchState
from agents import select_assistant, generate_search_queries, perform_web_searches, summarize_searh_results

# Add Nodes
graph = StateGraph(ResearchState)
graph.add_node("select_assistant", select_assistant)
graph.add_node("generate_search_queries", generate_search_queries)
graph.add_node("perform_web_searches", perform_web_searches)
graph.add_node("summarize_searh_results", summarize_searh_results)

# Add Edge
graph.add_edge("select_assistant", "generate_search_queries")
graph.add_edge("generate_search_queries", "perform_web_searches")
graph.add_edge("perform_web_searches", "summarize_searh_results")
graph.add_edge("summarize_searh_results", END)

# Set the entry point
graph.set_entry_point("select_assistant")

# Compile the graph
app = graph.compile()

initial_state = {
    "user_question": "What can you tell me about Astorga's roman spas",
    "assistant_info": None,
    "search_queries": None,
    "search_results": None,
    "search_summaries": None,
    "research_summary": None
}

result = app.invoke(initial_state)

final_report = result["search_summaries"]
print(final_report)

