import os
from dotenv import load_dotenv
from typing import List
import gradio as gr
from functools import partial
from styles import CSS, JS, EXAMPLES, HEADER_HTML
from pydantic import BaseModel, Field
from agents import Agent, ModelSettings, Runner, trace
from research_manager import ResearchManager
from clarifying_questions_agent import clarifying_questions_agent
from planner_agent import planner_agent
from search_agent import search_agent
from writer_agent import writer_agent
from email_agent import email_agent

from agent_config import get_default_model

load_dotenv(override=True)

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

NUM_CLARIFYING_QUESTIONS = 3

# --------------------------------------------------------------------------
# Structured Outputs
# --------------------------------------------------------------------------

# 1. Pydantic schema designed to map data structurally to your dynamic components
#The agent MUST respond matching this exact structural format
class DeepResearchSchema(BaseModel):
    status_text: str = Field(description="Status message showing the agent's current operation phase.")
    is_asking_clarifying_questions: bool = Field(description="True when the user is first asked to answer clarifying questions. Else it's false, like when continuing with deep research report.")
    questions_list: List[str] = Field(description="The list of dynamically generated or filtered questions.")
    final_report: str = Field(description="A comprehensive final report based on the overall operation state.")
    show_submit_row: bool = Field(description="Whether the answers submit button row should be visible to the user.")

# --------------------------------------------------------------------------
# Agents
# --------------------------------------------------------------------------

require_tool_setting = ModelSettings(tool_choice="required")

tools = [
    clarifying_questions_agent.as_tool(
        tool_name="clarifying_questions_agent",
        #tool_description="Use this tool to generate questions that the user would answer which clarify the user's real intent for their original query to which they want do get a deep research report by providing more context around the original query. Only ask it to generate the additional questions if appropriate."),
        tool_description="Use this tool to come up with clarifying questions to the user's query."),
    planner_agent.as_tool(
        tool_name="planner_agent", 
        tool_description="Use this tool generate web search queries that can be used to do web searches around the user's query and if appropriate additional context they provided as answers to clarifying questions. Just give it all appropriate context and ask it to generate the web searches and nothing else."),
    search_agent.as_tool(
        tool_name="search_agent", 
        tool_description="Use this tool to search the web given a query to search for. Just give it the query and ask it to execute the web search on it using its available tools. If multiple web searches are needed, then this tool must be called in parallel for each query."),
    writer_agent.as_tool(
        tool_name="writer_agent", 
        tool_description="Use this tool to generate the consolidated report for the user's query and additional context based on the web searches performed. Just give it the original query and each web search result and ask for the cohesive report."),
    email_agent.as_tool(
        tool_name="email_agent", 
        tool_description="Use this tool to send an email with the report contents.")
]


instructions = f"""
You are a deep research manager. Your goal is to provide a detailed report and 
send it to the user via email given a user's input. 

Step 1: If the user's initial input could be further refined, then you must come up with
clarifying questions via your clarifying_questions_agent tool and return exactly {NUM_CLARIFYING_QUESTIONS} of these so that they can be shown to 
the user who will answer and send back to you and this must be taken into 
account in addition to the user's initial input when continuing with the next steps
of the deep research. CRITICAL REQUIREMENT: You must pass along the same exact number of items provided by the tool used. 
Do NOT summarize, truncate, combine, or omit any items. You should can only ask clarifying questions once, so once the user has answered the questions, move on to the next step.

For the next steps, you are required to run all of these until the end, you can't return with a partial output and must only return when the report has been generated and you MUST use each tool available for the task.
Step 2: In either case (whether just with the user's initial query or with the initial 
query plus additional context), you must use the context provided to then come 
up with web search queries that will help answer the user's query and optional 
additional context using your planner tool. You must use the planner_agent tool for this.

Step 3: These queries shall then be used to perform web searches using your search_agent tool. If 
they're multiple web searches, then the tool must be called in parallel for 
each web search needed. You must use the search_agent for this and it must be done in parallel for all web searches.

Step 4: All of the web search results will then need to be analysed and synthesized to
come up with the final report to answer the user's query and optional 
additional context using your writer_agent tool. You must use the writer_agent for this.

Step 5: The report also needs to be sent via email to the user using your email_agent tool. You must use the writer_agent for this.

Step 6: Return the actual report as written by the writer_agent tool. Don't try to summarize it or chnage it in any way.

General: You have tools at your disposal which you must use at each step as mentioned, and you cannot return until you reach your goal which is to have a report generated and sent via email.
"""

#Follow these steps:
#1. analyze the user's initial input and ask clarifying questions if necessary: 
#The user's initial input is the presumably the topic that the user wants 
#you to do deep research on. A user's initial intent usually needs clarification, 
#so decide if this is the case and if there is anything that you can ask the user 
#to clarify what exactly you'll be researching, then you must ask clarifying 
#questions using the clarifying questions agent tool and stop processing further

#2. 

#model = get_default_model()
model = "gpt-5.4-mini"

deep_research_agent = Agent(name="Deep Research Agent", instructions=instructions, tools=tools, model=model, model_settings=require_tool_setting, output_type=DeepResearchSchema)

#come up with a set of web searches
#to perform to best answer the query. Output {HOW_MANY_SEARCHES} terms to query for.

def _format_qa_block(questions: List[str], answers: List[str]) -> str:
    lines = []
    for q, a in zip(questions, answers):
        a = (a or "").strip() or "(no answer given)"
        lines.append(f"Q: {q}\nA: {a}")
    return "\n".join(lines)

async def handle_button_click_via_agent(source, *args):
    
    #1 format input into 1 string, regardless of it being the initial query or the mutliple clarifications
    # if triggered by the original question (first interaction)
    if source == "ask_btn":
        original_question = (args[0] or "").strip()
        deep_research_context = f"Query: {(args[0] or "").strip()}"

    #else triggered by the clarifications
    elif source == "submit_answers_btn":
        original_question = args[0]
        questions = args[1]
        answers = args[2:] # Slurps up the rest of the *answer_boxes

        qa_block = _format_qa_block(questions, list(answers))
        deep_research_context = (
            f"Original question: {original_question}\n\n"
            f"Clarifying Q&A:\n{qa_block}\n\n"
        )

    #2 call the orchestrating agent
    #result = await Runner.run(deep_research_agent, f"Query: {deep_research_context}")
    with trace("deep research manager"):
        result = await Runner.run(deep_research_agent, deep_research_context)

    #3 figure out what the agent did
    #if it asked clarifying questions, then format the UI's clarifying questions components appropriately
    if result.final_output.is_asking_clarifying_questions and len(result.final_output.questions_list) > 0:
        questions = result.final_output.questions_list[:NUM_CLARIFYING_QUESTIONS]

        # Two separate update lists: one for the question-text Markdown, one for
        # the Column that wraps it + its textbox. Keeping the textbox's own label
        # static (set once at creation) avoids changing label+value+visible on
        # the same component in a single event, which is what caused the last
        # component to sometimes render a stale/spinner state until a second click.
        question_text_updates = [gr.update(value=f"**{q}**") for q in questions]
        column_updates = [gr.update(visible=True) for _ in questions]
        answer_box_updates = [gr.update(value="") for _ in questions]

        #reset the clarifying questions to empty
        result.final_output.questions_list = []

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
    #else if it generated the report, format the UI report component
    elif result.final_output.final_report:
        yield result.final_output.final_report

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
        fn=partial(handle_button_click_via_agent, "ask_btn"),
        inputs=[query_textbox],
        outputs=all_ui_outputs
    )

     # --- Event 2: Submit Answers Click ---
    submit_answers_btn.click(
        fn=partial(handle_button_click_via_agent, "submit_answers_btn"),
        inputs=[original_question_state, questions_state, *answer_boxes],
        outputs=[report]
    )

if __name__ == "__main__":
    ui.queue().launch(css=CSS, js=JS, theme=gr.themes.Base())

