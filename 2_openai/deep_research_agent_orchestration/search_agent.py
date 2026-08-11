from agents import Agent, FunctionTool, WebSearchTool, ModelSettings
from agent_config import get_default_model
from duckduckgo import local_web_search
import os

from dotenv import load_dotenv

load_dotenv(override=True)

INSTRUCTIONS = """
You are a research assistant. Given a search term, you search the web for that term and 
produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 words.
Capture the main points and be succinct. Reply only with the summary.
"""

settings = ModelSettings(tool_choice="required")

if os.getenv("DEFAULT_AI_PROVIDER") == "ollama":
    tools = [local_web_search]
else:
    tools = [WebSearchTool()]

model = get_default_model()
search_agent = Agent(name="Search Agent", instructions=INSTRUCTIONS, tools=tools, model=model, model_settings=settings)