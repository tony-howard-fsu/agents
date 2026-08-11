"""
Human-in-the-loop Flow around the EngineeringTeam crew (crew.py).

The manager (Process.hierarchical, manager_llm) delegates design_task /
code_task / frontend_task / test_task to engineering_lead / backend_engineer /
frontend_engineer / test_engineer, based on the `requirements` text. A human
launches the resulting app, tests it hands-on, then approves or requests a
targeted revision to a specific area.

Every targeted redo (design, backend, or frontend) runs a bidirectional
consistency check against whichever other area could be affected, so
cross-cutting breaks the human didn't explicitly ask about still get caught.
Every redo also runs the test suite and, if it fails, attempts to fix
whichever side is responsible and retest — capped at MAX_TEST_FIX_ATTEMPTS
tries — before handing control back to the human regardless of outcome.

Requires: crewai >= 1.8.0 (for the @human_feedback decorator)
"""

from crewai import Agent, Crew, Process, Task
from crewai.flow.flow import Flow, start, listen, or_
from crewai.flow.human_feedback import human_feedback, HumanFeedbackResult
from pydantic import BaseModel
from typing import Literal
import json
import re

import engineering_team.patch  # noqa: F401 — applies CrewAI MCP monkey-patch on import
from engineering_team.crew import EngineeringTeam
from .tools.sandbox_tools import sandbox_tools, reset_sandbox


# ---------------------------------------------------------------------------
# Flow-orchestration constants, structured-output models, and helpers.
# These belong here rather than in crew.py: crew.py just describes the
# EngineeringTeam crew itself, while these are all about how the human-in-
# the-loop review loop is orchestrated around it.
# ---------------------------------------------------------------------------

# Max number of automatic fix-and-retest attempts before giving up and handing
# control back to the human regardless of test outcome. Keeps the auto-fix
# loop bounded instead of retrying indefinitely on a failure it can't resolve.
MAX_TEST_FIX_ATTEMPTS = 2


class ConsistencyCheck(BaseModel):
    backend_needs_update: bool
    backend_reason: str
    frontend_needs_update: bool
    frontend_reason: str


class SingleConsistencyCheck(BaseModel):
    needs_update: bool
    reason: str


class TestVerdict(BaseModel):
    passed: bool
    failing_area: Literal["backend", "frontend", "both", "none"]
    summary: str


def _extract_json(text: str) -> str:
    """Best-effort strip of markdown code fences / surrounding prose, so a
    JSON parse can still succeed even if the model wraps its answer in
    ```json ... ``` or adds a short explanation before/after it."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def rerun_single(agent, description, expected_output, output_pydantic=None):
    """Run a single agent as a mini standalone crew — used for targeted
    redos/fixes/checks instead of re-kicking off the whole EngineeringTeam crew.

    Structured output (output_pydantic) is requested via prompting and parsed
    manually with Python's json, rather than using CrewAI's built-in
    output_pydantic/response_format machinery. That machinery calls the
    provider's native structured-output API, which some OpenAI-compatible
    endpoints (e.g. DeepSeek) don't support and will reject with a 400 error.
    Asking for plain JSON text and parsing it ourselves works with any model.
    """
    if output_pydantic is not None:
        schema = output_pydantic.model_json_schema()
        description = (
            f"{description}\n\n"
            f"Respond with ONLY a single valid JSON object — no markdown code "
            f"fences, no extra commentary before or after it — matching this "
            f"schema exactly:\n{json.dumps(schema)}"
        )
        expected_output = f"A single raw JSON object matching the given schema. {expected_output}"

    task = Task(description=description, expected_output=expected_output, agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
    result = crew.kickoff()

    if output_pydantic is not None:
        return output_pydantic.model_validate_json(_extract_json(result.raw))
    return result.raw


# ---------------------------------------------------------------------------
# Reviewer agent — not one of the four delegated engineering roles, so it's
# defined here rather than in the EngineeringTeam crew, and never becomes
# part of the main hierarchical crew's roster (it's only ever used via
# rerun_single, for one-off consistency checks). Content mirrors the
# `reviewer:` entry in agents.yaml, kept in sync manually since this one
# isn't loaded from that config.
# ---------------------------------------------------------------------------

reviewer = Agent(
    role="Integration Reviewer.",
    goal="Determine whether a design change breaks existing backend/frontend work.",
    backstory=(
        "A meticulous engineer who checks cross-team consistency before signing off on "
        "changes. Conservative by nature: when it's ambiguous whether a design change "
        "affects backend or frontend, this engineer flags it for review rather than "
        "assuming it's fine. A missed inconsistency causing a broken build is far worse "
        "than an unnecessary review."
    ),
    tools=sandbox_tools,
    allow_delegation=False,
    llm="deepseek/deepseek-v4-pro",
)


class ReviewState(BaseModel):
    requirements: str = ""
    design_output: str = ""
    backend_output: str = ""
    frontend_output: str = ""
    test_output: str = ""
    revision_count: int = 0
    feedback_history: list[str] = []


class ProductDevFlow(Flow[ReviewState]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Instantiate once and reuse across the flow, so @agent-decorated
        # methods keep returning the same cached agent instances rather than
        # rebuilding fresh ones (and losing any accumulated agent-level state)
        # on every redo.
        self.team = EngineeringTeam()

    def compiled_output(self):
        s = self.state
        return (
            f"=== DESIGN ===\n{s.design_output}\n\n"
            f"=== BACKEND ===\n{s.backend_output}\n\n"
            f"=== FRONTEND ===\n{s.frontend_output}\n\n"
            f"=== TEST ===\n{s.test_output}"
        )

    def feedback_history_text(self) -> str:
        if not self.state.feedback_history:
            return "(no prior feedback yet — this is the first round of revision)"
        return "\n".join(self.state.feedback_history)

    def run_tests(self) -> TestVerdict:
        verdict: TestVerdict = rerun_single(
            self.team.test_engineer(),
            f"Re-run testing for {self.state.requirements} against the current backend and "
            f"frontend code (read the actual current files, not summaries). Report whether "
            f"everything passes. If not, identify which area is most likely responsible for "
            f"the failure(s) — backend, frontend, or both — based on where the actual bug "
            f"lives, not just where the symptom shows up.\n\n"
            f"Design:\n{self.state.design_output}",
            "A structured test verdict",
            output_pydantic=TestVerdict,
        )
        self.state.test_output = verdict.summary
        return verdict

    def resolve_test_failures(self):
        for _ in range(MAX_TEST_FIX_ATTEMPTS):
            verdict = self.run_tests()
            if verdict.passed:
                return

            if verdict.failing_area in ("backend", "both"):
                self.state.backend_output = rerun_single(
                    self.team.backend_engineer(),
                    f"Tests are failing for {self.state.requirements}. Read the existing backend "
                    f"files and fix the issue in place — do not rewrite from scratch.\n\n"
                    f"Design:\n{self.state.design_output}\n\n"
                    f"Test failure summary: {verdict.summary}",
                    "Confirmation of backend files fixed and how to run the service",
                )
            if verdict.failing_area in ("frontend", "both"):
                self.state.frontend_output = rerun_single(
                    self.team.frontend_engineer(),
                    f"Tests are failing for {self.state.requirements}. Read the existing frontend "
                    f"files and fix the issue in place — do not rewrite from scratch.\n\n"
                    f"Design:\n{self.state.design_output}\n\n"
                    f"Test failure summary: {verdict.summary}",
                    "Confirmation of frontend files fixed and how to launch the app",
                )

        # Ran out of attempts — do one last pass so state.test_output reflects
        # the true current status, then hand back to the human regardless.
        self.run_tests()

    @start()
    def run_crew(self):
        reset_sandbox()
        result = self.team.crew().kickoff(inputs={"requirements": self.state.requirements})

        # Order matches the @task method definition order in EngineeringTeam:
        # design_task, code_task, frontend_task, test_task
        outs = result.tasks_output
        self.state.design_output = outs[0].raw
        self.state.backend_output = outs[1].raw
        self.state.frontend_output = outs[2].raw
        self.state.test_output = outs[3].raw
        return self.compiled_output()

    @human_feedback(
        message=(
            "The app has been built/updated — go launch it and try it out yourself. "
            "Once you've tested it, approve, or describe what needs to change "
            "(mention design/backend/frontend/test):"
        ),
        emit=["approved", "revise_design", "revise_backend", "revise_frontend", "revise_test"],
        llm="deepseek/deepseek-v4-pro",
        default_outcome="approved",
    )
    @listen(or_("run_crew", "redo_design", "redo_backend", "redo_frontend", "redo_test"))
    def review(self):
        return self.compiled_output()

    @listen("revise_design")
    def redo_design(self, result: HumanFeedbackResult):
        self.state.revision_count += 1
        self.state.feedback_history.append(
            f"Round {self.state.revision_count} (design): {result.feedback}"
        )
        self.state.design_output = rerun_single(
            self.team.engineering_lead(),
            f"Revise the architecture design for {self.state.requirements}.\n\n"
            f"Previous design:\n{self.state.design_output}\n\n"
            f"All feedback given so far, across every round of revision — keep all of "
            f"this in mind, not just the most recent round:\n{self.feedback_history_text()}\n\n"
            f"Feedback from the human, based on hands-on testing of the running app "
            f"(most recent round): {result.feedback}",
            "Updated architecture doc",
        )

        check: ConsistencyCheck = rerun_single(
            reviewer,
            "Compare the NEW design below against the EXISTING backend and frontend code "
            "(read the actual current files, not summaries). For each, decide if it now "
            "contradicts the design (e.g. changed data model, changed API contract, changed "
            "UI requirements) or if it's still compatible (e.g. wording/naming-only change).\n\n"
            "When uncertain, err on the side of flagging it as needing an update — "
            "a false positive costs one extra revision, but a false negative ships a broken build.\n\n"
            f"NEW DESIGN:\n{self.state.design_output}",
            "A structured consistency verdict",
            output_pydantic=ConsistencyCheck,
        )

        if check.backend_needs_update:
            self.state.backend_output = rerun_single(
                self.team.backend_engineer(),
                f"Revise the backend for {self.state.requirements} to match the updated design. "
                f"Read the existing backend files and edit them in place — do not rewrite "
                f"from scratch or just describe the change.\n"
                f"Why it needs to change: {check.backend_reason}\n\n"
                f"Updated design:\n{self.state.design_output}",
                "Confirmation of backend files updated and how to run the service",
            )
        if check.frontend_needs_update:
            self.state.frontend_output = rerun_single(
                self.team.frontend_engineer(),
                f"Revise the frontend for {self.state.requirements} to match the updated design. "
                f"Read the existing frontend files and edit them in place — do not rewrite "
                f"from scratch or just describe the change.\n"
                f"Why it needs to change: {check.frontend_reason}\n\n"
                f"Updated design:\n{self.state.design_output}",
                "Confirmation of frontend files updated and how to launch the app",
            )

        self.resolve_test_failures()
        return self.state.design_output

    @listen("revise_backend")
    def redo_backend(self, result: HumanFeedbackResult):
        self.state.revision_count += 1
        self.state.feedback_history.append(
            f"Round {self.state.revision_count} (backend): {result.feedback}"
        )
        self.state.backend_output = rerun_single(
            self.team.backend_engineer(),
            f"Revise the backend for {self.state.requirements}. Read the existing backend files "
            f"and edit them in place based on the feedback below — do not just describe the "
            f"change.\n\n"
            f"Architecture (unchanged):\n{self.state.design_output}\n\n"
            f"All feedback given so far, across every round of revision — keep all of "
            f"this in mind, not just the most recent round:\n{self.feedback_history_text()}\n\n"
            f"Feedback from the human, based on hands-on testing of the running app "
            f"(most recent round): {result.feedback}",
            "Confirmation of backend files updated and how to run the service",
        )

        check: SingleConsistencyCheck = rerun_single(
            reviewer,
            "The backend for this app was just changed. Compare the NEW backend against the "
            "EXISTING frontend (read the actual current files, not summaries) and decide "
            "whether the frontend now needs updating to stay consistent — e.g. a changed API "
            "contract, changed response shape, or changed error format it relies on.\n\n"
            "When uncertain, err on the side of flagging it as needing an update — "
            "a false positive costs one extra revision, but a false negative ships a broken build.\n\n"
            f"Design (for context):\n{self.state.design_output}",
            "A structured consistency verdict",
            output_pydantic=SingleConsistencyCheck,
        )
        if check.needs_update:
            self.state.frontend_output = rerun_single(
                self.team.frontend_engineer(),
                f"Update the frontend for {self.state.requirements} to stay consistent with a "
                f"recent backend change. Read the existing frontend files and edit them in "
                f"place — do not rewrite from scratch.\n"
                f"Why it needs to change: {check.reason}\n\n"
                f"Design (for context):\n{self.state.design_output}",
                "Confirmation of frontend files updated and how to launch the app",
            )

        self.resolve_test_failures()
        return self.state.backend_output

    @listen("revise_frontend")
    def redo_frontend(self, result: HumanFeedbackResult):
        self.state.revision_count += 1
        self.state.feedback_history.append(
            f"Round {self.state.revision_count} (frontend): {result.feedback}"
        )
        self.state.frontend_output = rerun_single(
            self.team.frontend_engineer(),
            f"Revise the frontend for {self.state.requirements}. Read the existing frontend files "
            f"and edit them in place based on the feedback below — do not just describe the "
            f"change.\n\n"
            f"Architecture (unchanged):\n{self.state.design_output}\n\n"
            f"All feedback given so far, across every round of revision — keep all of "
            f"this in mind, not just the most recent round:\n{self.feedback_history_text()}\n\n"
            f"Feedback from the human, based on hands-on testing of the running app "
            f"(most recent round): {result.feedback}",
            "Confirmation of frontend files updated and how to launch the app",
        )

        check: SingleConsistencyCheck = rerun_single(
            reviewer,
            "The frontend for this app was just changed. Compare the NEW frontend against the "
            "EXISTING backend (read the actual current files, not summaries) and decide "
            "whether the backend now needs updating to stay consistent — e.g. the frontend "
            "now expects a field, endpoint, or behavior the backend doesn't currently provide.\n\n"
            "When uncertain, err on the side of flagging it as needing an update — "
            "a false positive costs one extra revision, but a false negative ships a broken build.\n\n"
            f"Design (for context):\n{self.state.design_output}",
            "A structured consistency verdict",
            output_pydantic=SingleConsistencyCheck,
        )
        if check.needs_update:
            self.state.backend_output = rerun_single(
                self.team.backend_engineer(),
                f"Update the backend for {self.state.requirements} to stay consistent with a "
                f"recent frontend change. Read the existing backend files and edit them in "
                f"place — do not rewrite from scratch.\n"
                f"Why it needs to change: {check.reason}\n\n"
                f"Design (for context):\n{self.state.design_output}",
                "Confirmation of backend files updated and how to run the service",
            )

        self.resolve_test_failures()
        return self.state.frontend_output

    @listen("revise_test")
    def redo_test(self, result: HumanFeedbackResult):
        self.state.revision_count += 1
        self.state.feedback_history.append(
            f"Round {self.state.revision_count} (test): {result.feedback}"
        )
        self.state.test_output = rerun_single(
            self.team.test_engineer(),
            f"Revise testing for {self.state.requirements}.\n\n"
            f"Backend:\n{self.state.backend_output}\n\nFrontend:\n{self.state.frontend_output}\n\n"
            f"Previous test report:\n{self.state.test_output}\n\n"
            f"All feedback given so far, across every round of revision — keep all of "
            f"this in mind, not just the most recent round:\n{self.feedback_history_text()}\n\n"
            f"Human feedback (most recent round): {result.feedback}",
            "Updated test report",
        )
        return self.state.test_output

    @listen("approved")
    def finalize(self, result: HumanFeedbackResult):
        print(f"Approved after {self.state.revision_count} revision(s):\n{self.compiled_output()}")
        return self.compiled_output()


if __name__ == "__main__":
    flow = ProductDevFlow()
    flow.kickoff(inputs={"requirements": "See main.py for the full requirements text"})