import os
from agents import ModelSettings, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

def get_default_model():
    """
    Returns the model to use for an Agent based on environment configuration.

    If DEFAULT_AI_PROVIDER is set, builds an OpenAIChatCompletionsModel
    pointed at the custom provider (base URL, API key, model name).
    Otherwise, falls back to the global MODEL_NAME.
    """

    if os.getenv("DEFAULT_AI_PROVIDER") != None:
        agent_client = AsyncOpenAI(
            base_url=os.getenv("DEFAULT_AI_PROVIDER_BASE_URL"),
            api_key=os.getenv("DEFAULT_AI_PROVIDER_API_KEY"),
        )
        model = OpenAIChatCompletionsModel(
            model=os.getenv("DEFAULT_MODEL_NAME"),
            openai_client=agent_client
        )
    else:
        model = os.getenv("DEFAULT_OPENAI_MODEL_NAME", "gpt-5.4-mini")

    return model