from functools import partial
import os
from typing import List
import gradio as gr
from pydantic import BaseModel
from dotenv import load_dotenv
from agents import Agent, Runner
from research_manager import ResearchManager
from clarifying_questions_agent import clarifying_questions_agent
from styles import CSS, JS, EXAMPLES, HEADER_HTML

load_dotenv(override=True)

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

NUM_CLARIFYING_QUESTIONS = 3

def _format_qa_block(questions: List[str], answers: List[str]) -> str:
    lines = []
    for q, a in zip(questions, answers):
        a = (a or "").strip() or "(no answer given)"
        lines.append(f"Q: {q}\nA: {a}")
    return "\n".join(lines)

async def handle_button_click_via_manager(source, *args):
    if source == "ask_btn":
        # 1. Unpack the inputs specific to the 'ask' button
        original_question = (args[0] or "").strip()
        result = await Runner.run(clarifying_questions_agent, original_question)
        questions = result.final_output.questions[:NUM_CLARIFYING_QUESTIONS]

        # Two separate update lists: one for the question-text Markdown, one for
        # the Column that wraps it + its textbox. Keeping the textbox's own label
        # static (set once at creation) avoids changing label+value+visible on
        # the same component in a single event, which is what caused the last
        # component to sometimes render a stale/spinner state until a second click.
        question_text_updates = [gr.update(value=f"**{q}**") for q in questions]
        column_updates = [gr.update(visible=True) for _ in questions]
        answer_box_updates = [gr.update(value="") for _ in questions]

        # 2. Return values for 'ask' outputs, and gr.update() for the 'report' component. Since report generation uses yield, entire function has to use yield
        yield (
            questions,  # questions_state
            original_question,  # original_question_state
            gr.update(value="", visible=False),  # status
            *question_text_updates,
            *column_updates,
            *answer_box_updates,
            gr.update(visible=True),  # answers_submit_row
            gr.update() # <-- Keeps the 'report' box unchanged during this phase
        )
        return
    elif source == "submit_answers_btn":
    #else:
        # 1. Unpack inputs specific to the 'submit_answers_btn' button
        # Because we passed a massive list to inputs=[...], unpack them carefully:
        original_question = args[0]
        questions = args[1]
        answers = args[2:] # Slurps up the rest of the *answer_boxes

        qa_block = _format_qa_block(questions, list(answers))
        research_input = (
            f"Original question: {original_question}\n\n"
            f"Clarifying Q&A:\n{qa_block}\n\n"
        )

        async for status_update in ResearchManager().run(research_input):
            yield status_update

# --------------------------------------------------------------------------
# Gradio UI
# --------------------------------------------------------------------------
with gr.Blocks(title="Deep Research") as ui:    
    gr.HTML(HEADER_HTML)

    original_question_state = gr.State("")
    questions_state = gr.State([])

    with gr.Row(elem_classes="dr-query-row"):
        query_textbox = gr.Textbox(
            placeholder="Type a research question...",
            show_label=False,
            container=False,
            autofocus=True,
            elem_id="dr-query",
            scale=5,
        )
        ask_btn = gr.Button("Ask", variant="primary", elem_id="dr-run", scale=1)

    gr.HTML('<div class="dr-examples-label">Try one</div>')
    gr.Examples(examples=EXAMPLES, inputs=query_textbox, elem_id="dr-examples")

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
        submit_answers_btn = gr.Button("Submit answers & research", variant="primary", elem_id="dr-run", scale=1)
    
    report = gr.Markdown(elem_id="dr-report")

    # Create a master list of all UI outputs that the function can potentially touch
    all_ui_outputs = [
        questions_state,
        original_question_state,
        status_box,
        *question_text_boxes,
        *question_columns,
        *answer_boxes,
        answers_submit_row,
        report, # <-- Added to the end of the master list
    ]

    # --- Event 1: Clarifying Questions Click ---
    ask_btn.click(
        fn=partial(handle_button_click_via_manager, "ask_btn"),
        inputs=[query_textbox],
        outputs=all_ui_outputs
    )

     # --- Event 2: Submit Answers Click ---
    submit_answers_btn.click(
        fn=partial(handle_button_click_via_manager, "submit_answers_btn"),
        inputs=[original_question_state, questions_state, *answer_boxes],
        outputs=[report]
    )

if __name__ == "__main__":
    ui.queue().launch(css=CSS, js=JS, theme=gr.themes.Base())

