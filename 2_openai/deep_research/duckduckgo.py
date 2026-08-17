import asyncio

from agents import function_tool
from ddgs import DDGS      # Free, local web search engine


def _search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if not results:
                return "No search results found."

            formatted_results = []
            for r in results:
                formatted_results.append(f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}\n---")
            return "\n".join(formatted_results)
    except Exception as e:
        return f"Search failed due to an error: {str(e)}"


@function_tool
async def local_web_search(query: str) -> str:
    """
    Searches the live internet for information on a given topic and returns a summary.

    Args:
        query (str): The search keywords or question to look up online.
    """
    # DDGS's .text() is a blocking network call; run it off the event loop so
    # ResearchManager.perform_searches()'s asyncio.gather over multiple searches
    # actually runs them concurrently instead of serializing on the loop.
    return await asyncio.to_thread(_search, query)