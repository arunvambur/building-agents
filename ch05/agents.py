from prompts import (
    ASSISTANT_SELECTION_PROMPT_TEMPLATE,
    WEB_SEARCH_PROMPT_TEMPLATE,
    SUMMARY_PROMPT_TEMPLATE
)
from llm_models import get_llm
import json
from utils.web_searching import web_search
from utils.web_scraping import web_scrape

NUM_SEARCH_QUERIES = 3
NUM_SEARCH_RESULTS_PER_QUERY = 3
RESULT_TEXT_MAX_CHARACTERS = 10000

def select_assistant(state: dict) -> dict:
    #select the appropriate search assistant
    user_question = state["user_question"]

    #Use the LLm to select an assistant
    prompt = ASSISTANT_SELECTION_PROMPT_TEMPLATE.format(
        user_question = user_question
    )
    response = get_llm().invoke(prompt)

    assistant_info = parse_assistant_info(response.content, user_question)

    return assistant_info

def parse_assistant_info(response_text, user_question):
     # Parse the response to get the assistant info
    try:
        # Extract the JSON part from the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        json_str = response_text[json_start:json_end]
        
        # Parse the JSON
        assistant_info = json.loads(json_str)
        
        # Return the updated state
        return {"assistant_info": assistant_info}
    except Exception as e:
        # Fallback to a default assistant if parsing fails
        default_assistant = {
            "assistant_type": "General research assistant",
            "assistant_instructions": "You are a general research AI assistant. Your main purpose is to draft comprehensive, informative, unbiased, and well-structured reports on given topics.",
            "user_question": user_question
        }
        return {"assistant_info": default_assistant}
    

def generate_search_queries(state: dict) -> dict:
    #Generate the search qureris based on the question.
    assistant_info = state["assistant_info"]
    user_question = state["user_question"]
    # Get the current iteration count
    iteration_count = state.get("iteration_count", 0)

    prompt = WEB_SEARCH_PROMPT_TEMPLATE.format(
        assistant_instructions=assistant_info["assistant_instructions"],
        user_question=user_question,
        num_search_queries=3
    )
    response = get_llm().invoke(prompt)

    search_queries = parse_search_queries(response.content, user_question, iteration_count)

    return search_queries

def parse_search_queries(response_text, user_question, iteration_count):
     # Parse the response to get the search queries
    try:
        # Extract the JSON array from the response
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        json_str = response_text[json_start:json_end]
        
        # Parse the JSON
        search_queries = json.loads(json_str)
        
        print(f"Generated {len(search_queries)} search queries")
        for i, query in enumerate(search_queries):
            print(f"  Query {i+1}: {query['search_query']}")
        
        # Return the updated state
        return {
            "search_queries": search_queries,
            # Reset the relevance evaluation and regeneration flag when generating new queries
            "relevance_evaluation": None,
            "should_regenerate_queries": None
        }
    except Exception as e:
        print(f"Error parsing search queries: {str(e)}")
        # Fallback to a default search query if parsing fails
        default_queries = [
            {"search_query": f"{user_question} iteration {iteration_count + 1}", "user_question": user_question}
        ]
        print(f"Using default query: {default_queries[0]['search_query']}")
        return {
            "search_queries": default_queries,
            "relevance_evaluation": None,
            "should_regenerate_queries": None
        }
    
def perform_web_searches(state: dict) -> dict:
    search_queries = state["search_queries"]
    search_results = []
    fallback_used = False

    for query_obj in search_queries:
        search_query = query_obj["search_query"]
        user_question = query_obj["user_question"]

        try:
            print(f"Searching for: {search_query}")
            urls = web_search(web_query=search_query, num_results=NUM_SEARCH_RESULTS_PER_QUERY)

            if any("wikipedia.org" in url for url in urls[:2]):
                print(f"Fallback search was used for query: {search_query}")
                fallback_used = True
                is_fallback = True
            else:
                is_fallback = False

            # Add results to the list
            for url in urls:
                search_results.append(
                    {
                        "result_url": url,
                        "search_query": search_query,
                        "user_question": user_question,
                        "is_fallback": is_fallback
                    }
                )

            print(f"Found {len(urls)} results for query: {search_query}")
        except Exception as e:
            print(f"Error searching for '{search_query}': {str(e)}")
            # Continue with other queries even if one fails
            continue

         # Return the updated state with information about fallback usage
    return {
        "search_results": search_results,
        "used_fallback_search": fallback_used
    }

def summarize_searh_results(state: dict) -> dict:
    search_results = state["search_results"]
    used_fallback_search = state.get("used_fallback_search", False)

    llm = get_llm()
    summaries = []

    print(f"Summarizing {len(search_results)} search results...")

    for result in search_results:
        result_url = result["result_url"]
        search_query = result["search_query"]
        user_question = result["user_question"]
        is_fallback = result.get("is_fallback", False)

        try:
            print(f"Scraping content from: {result_url}")
            search_result_text = web_scrape(url = result_url)[:RESULT_TEXT_MAX_CHARACTERS]

             # Skip if the content is an error message or too short
            if search_result_text.startswith("Failed to") or len(search_result_text) < 50:
                print(f"Skipping {result_url} due to scraping issues or insufficient content")
                continue

            prompt = SUMMARY_PROMPT_TEMPLATE.format(
                            search_result_text=search_result_text,
                            search_query=search_query
                        )

            response = llm.invoke(prompt)

            summary = {
                "summary": f"Source Url: {result_url}\nSummary: {response.content}",
                "result_url": result_url,
                "user_question": user_question,
                "is_fallback": is_fallback
            }

            summaries.append(summary())
            print(f"Successfully summarized content from: {result_url}")
        except Exception as e:
            print(f"Error summarizing {result_url}: {str(e)}")
            # Skip this result if there's an error
            continue


    research_summary = "\n\n".join([s["summary"] for s in summaries])
    print(f"Created research summary with {len(summaries)} sources")



    return {
        "search_summaries": summaries,
        "research_summary": research_summary,
        "used_fallback_search": used_fallback_search
    }




