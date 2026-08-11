"""
Gradio app: user asks a question -> LLM asks N clarifying questions (once) ->
user answers -> LLM defines M web search queries -> agent runs those searches
and synthesizes a final answer.

Requirements:
    pip install openai-agents gradio

Env:
    export OPENAI_API_KEY=sk-...

Run:
    python app.py
"""

import os
from dotenv import load_dotenv
from typing import List

import gradio as gr
from pydantic import BaseModel

from agents import Agent, Runner, WebSearchTool

load_dotenv(override=True)

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

NUM_CLARIFYING_QUESTIONS = 3
NUM_SEARCH_QUERIES = 4
MODEL = "gpt-5.1"  # swap for whichever model you have access to


# --------------------------------------------------------------------------
# Structured outputs
# --------------------------------------------------------------------------

class ClarifyingQuestions(BaseModel):
    questions: List[str]


class SearchQueries(BaseModel):
    queries: List[str]


# --------------------------------------------------------------------------
# Agents
# --------------------------------------------------------------------------

clarifying_agent = Agent(
    name="Clarifying Agent",
    model=MODEL,
    instructions=(
        "A user will give you a question. Before it can be answered well, you need "
        f"more information. Generate exactly {NUM_CLARIFYING_QUESTIONS} short, specific "
        "clarifying questions that would most help narrow down and best answer the "
        "user's original question. Do not answer the question yourself. Do not ask "
        f"more or fewer than {NUM_CLARIFYING_QUESTIONS} questions."
    ),
    output_type=ClarifyingQuestions,
)

query_planning_agent = Agent(
    name="Query Planning Agent",
    model=MODEL,
    instructions=(
        "You will be given a user's original question, along with clarifying questions "
        "and the user's answers to them. Based on all of this context, generate exactly "
        f"{NUM_SEARCH_QUERIES} distinct, specific web search queries that together would "
        "best gather the information needed to answer the user's original question well. "
        "Return only the queries, no commentary."
    ),
    output_type=SearchQueries,
)

research_agent = Agent(
    name="Research Agent",
    model=MODEL,
    instructions=(
        "You are a research assistant. You will be given a user's original question, "
        "clarifying Q&A, and a fixed list of web search queries that have already been "
        "decided on. Call the web search tool once for each listed query, using the "
        "query text as given, then synthesize everything you find into one clear, "
        "well-organized answer to the user's original question. Mention sources/URLs "
        "where useful."
    ),
    tools=[WebSearchTool()],
)


# --------------------------------------------------------------------------
# Step 1: original question -> clarifying questions
# --------------------------------------------------------------------------

async def ask_clarifying_questions(original_question: str):
    original_question = (original_question or "").strip()

    if not original_question:
        # Nothing entered yet: keep clarifying columns hidden, show a nudge.
        no_change_text = [gr.update() for _ in range(NUM_CLARIFYING_QUESTIONS)]
        hidden_columns = [gr.update(visible=False) for _ in range(NUM_CLARIFYING_QUESTIONS)]
        no_change_answers = [gr.update() for _ in range(NUM_CLARIFYING_QUESTIONS)]
        return (
            [],  # questions_state
            original_question,  # original_question_state
            gr.update(value="Please enter a question first.", visible=True),  # status
            *no_change_text,
            *hidden_columns,
            *no_change_answers,
            gr.update(visible=False),  # answers_submit_row
        )

    result = await Runner.run(clarifying_agent, original_question)
    questions = result.final_output.questions[:NUM_CLARIFYING_QUESTIONS]

    # Pad in case the model returns fewer than requested.
    while len(questions) < NUM_CLARIFYING_QUESTIONS:
        questions.append(f"Anything else relevant to: '{original_question}'?")

    # Two separate update lists: one for the question-text Markdown, one for
    # the Column that wraps it + its textbox. Keeping the textbox's own label
    # static (set once at creation) avoids changing label+value+visible on
    # the same component in a single event, which is what caused the last
    # component to sometimes render a stale/spinner state until a second click.
    question_text_updates = [gr.update(value=f"**{q}**") for q in questions]
    column_updates = [gr.update(visible=True) for _ in questions]
    answer_box_updates = [gr.update(value="") for _ in questions]

    return (
        questions,  # questions_state
        original_question,  # original_question_state
        gr.update(value="", visible=False),  # status
        *question_text_updates,
        *column_updates,
        *answer_box_updates,
        gr.update(visible=True),  # answers_submit_row
    )


# --------------------------------------------------------------------------
# Step 2: answers -> search queries -> web search -> final answer
# --------------------------------------------------------------------------

def _format_qa_block(questions: List[str], answers: List[str]) -> str:
    lines = []
    for q, a in zip(questions, answers):
        a = (a or "").strip() or "(no answer given)"
        lines.append(f"Q: {q}\nA: {a}")
    return "\n".join(lines)


async def run_research(original_question, questions, *answers):
    original_question = (original_question or "").strip()
    if not original_question:
        return "Please ask a question first.", ""

    qa_block = _format_qa_block(questions, list(answers))

    planning_input = (
        f"Original question: {original_question}\n\n"
        f"Clarifying Q&A:\n{qa_block}"
    )
    plan_result = await Runner.run(query_planning_agent, planning_input)
    queries = plan_result.final_output.queries[:NUM_SEARCH_QUERIES]

    queries_block = "\n".join(f"- {q}" for q in queries)

    research_input = (
        f"Original question: {original_question}\n\n"
        f"Clarifying Q&A:\n{qa_block}\n\n"
        f"Search queries to run (run every one of these):\n{queries_block}"
    )
    research_result = await Runner.run(research_agent, research_input)

    return research_result.final_output, queries_block


# --------------------------------------------------------------------------
# Gradio UI
# --------------------------------------------------------------------------

with gr.Blocks(title="Clarify & Research") as demo:
    gr.Markdown("## Ask a question\nThe assistant may ask a few clarifying questions before researching.")

    original_question_state = gr.State("")
    questions_state = gr.State([])

    with gr.Row():
        question_input = gr.Textbox(
            label="Your question", placeholder="What do you want to know?", scale=4
        )
        ask_btn = gr.Button("Start", variant="primary", scale=1)

    status_box = gr.Markdown(visible=False)

    # Each clarifying question is a Column whose visibility is the only thing
    # toggled after creation. The question text is a separate Markdown, and
    # the answer Textbox keeps a static label ("Your answer") set once at
    # creation. Avoiding simultaneous label+value+visible changes on one
    # component is what fixes the "last box shows a spinner until a second
    # click" rendering glitch.
    question_text_boxes = []
    answer_boxes = []
    question_columns = []
    for i in range(NUM_CLARIFYING_QUESTIONS):
        with gr.Column(visible=False) as col:
            q_text = gr.Markdown(f"**Clarifying question {i + 1}**")
            a_box = gr.Textbox(label="Your answer")
        question_columns.append(col)
        question_text_boxes.append(q_text)
        answer_boxes.append(a_box)

    with gr.Row(visible=False) as answers_submit_row:
        submit_answers_btn = gr.Button("Submit answers & research", variant="primary")

    queries_used_box = gr.Markdown(label="Search queries used")
    final_answer_box = gr.Markdown(label="Answer")

    ask_btn.click(
        fn=ask_clarifying_questions,
        inputs=[question_input],
        outputs=[
            questions_state,
            original_question_state,
            status_box,
            *question_text_boxes,
            *question_columns,
            *answer_boxes,
            answers_submit_row,
        ],
    )

    submit_answers_btn.click(
        fn=run_research,
        inputs=[original_question_state, questions_state, *answer_boxes],
        outputs=[final_answer_box, queries_used_box],
    )


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY is not set in the environment.")
    demo.queue().launch()