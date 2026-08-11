from agents import function_tool
from ddgs import DDGS      # Free, local web search engine

@function_tool
def local_web_search(query: str) -> str:
    """
    Searches the live internet for information on a given topic and returns a summary.
    
    Args:
        query (str): The search keywords or question to look up online.
    """
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