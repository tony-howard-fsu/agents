import os
from dotenv import load_dotenv
from typing import List
from pydantic import BaseModel, Field
from agents import Agent
from agent_config import get_default_model

load_dotenv(override=True)

NUM_CLARIFYING_QUESTIONS = 3

# --------------------------------------------------------------------------
# Structured outputs
# --------------------------------------------------------------------------

class ClarifyingQuestions(BaseModel):
    questions: List[str]

# --------------------------------------------------------------------------
# Agents
# --------------------------------------------------------------------------
model = get_default_model()

INSTRUCTIONS = f"""
A user will give you a question. Before it can be answered well, you need 
more information. Generate exactly {NUM_CLARIFYING_QUESTIONS} short, specific 
clarifying questions that would most help narrow down and best answer the 
user's original question. Do not answer the question yourself. Do not ask 
more or fewer than {NUM_CLARIFYING_QUESTIONS} questions. You must always 
respond in valid JSON format and follow the structured output specified.
"""


clarifying_questions_agent = Agent(
    name="Clarifying Questions Agent",
    model=model,
    instructions=INSTRUCTIONS,
    output_type=ClarifyingQuestions,
)