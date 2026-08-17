"""The two models the agent loop uses, kept in one place so they are easy to swap.

Both are "provider/model-id" strings, e.g. "deepseek/deepseek-v4-flash" or
"openai/gpt-5.5" — the provider prefix is what makes each side routable to any
backend without touching code:

  - ORCHESTRATOR_MODEL feeds orchestrator_llm() below, which wraps it in ADK's
    LiteLlm for every provider (LiteLLM reads the matching *_API_KEY from the
    environment by its standard name — DEEPSEEK_API_KEY, OPENAI_API_KEY,
    GOOGLE_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, ...). orchestrator.py,
    css_agent.py and qa_agent.py all build their ADK agent through this helper.
  - WORKER_MODEL is read the same way by each of the five worker scripts, which
    resolve it through their own worker_llm.resolve() (see 2_strands_pydantic/
    and 3_maf_agno/) into the base_url + api key their OpenAI-compatible client
    needs; Mastra's worker.ts does the same via providers.ts.

Set either as an env var for a one-off run, or edit the defaults here.
"""

import os

ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "deepseek/deepseek-v4-flash")  # cheaper: deepseek/deepseek-v4-flash-lite
WORKER_MODEL = os.environ.get("WORKER_MODEL", "deepseek/deepseek-v4-pro")  # cheaper: deepseek/deepseek-v4-flash


def orchestrator_llm():
    """The orchestrator model, wrapped for ADK's LiteLLM route. Imported lazily so
    importing config on its own never pulls in ADK before a caller has had the
    chance to call quiet.silence() first."""
    from google.adk.models.lite_llm import LiteLlm

    return LiteLlm(model=ORCHESTRATOR_MODEL)
