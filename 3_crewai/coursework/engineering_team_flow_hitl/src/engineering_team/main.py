#!/usr/bin/env python
import sys
import warnings
from datetime import datetime

import engineering_team.patch  # noqa: F401 — applies CrewAI MCP monkey-patch on import
from engineering_team.crew import EngineeringTeam
from engineering_team.flow import ProductDevFlow
from .tools.sandbox_tools import reset_sandbox

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

requirements = """
A simple account management system for a trading simulation platform.
The system should allow users to create an account, deposit funds, and withdraw funds.
The system should allow users to record that they have bought or sold shares, providing a quantity.
The system should calculate the total value of the user's portfolio, and the profit or loss from the initial deposit.
The system should be able to report the holdings of the user at any point in time.
The system should be able to report the profit or loss of the user at any point in time.
The system should be able to list the transactions that the user has made over time.
The system should prevent the user from withdrawing funds that would leave them with a negative balance, or
 from buying more shares than they can afford, or selling shares that they don't have.
 The system has access to a function get_share_price(symbol) which returns the current price of a share, and includes a test implementation that returns fixed prices for AAPL, TSLA, GOOGL.
The UI should always have a visible area to create an account.
If there is no existing account, the UI should allow the user to create one and no other menu options should be visible.
If there is an existing account, the UI should allow the user to deposit funds, withdraw funds, and no other menu options should be visible as different tabs at the same level of the UI menu.
Even if there is an existing account, the UI should allow the user to create a new account. This should be a separate tab at the same level of the profile menu/tab.
There should be a profile menu tab that allows the user to select an account as the upper-most UI area. Below it, there should be another area that holds the other menu options as tabs.
All data should be visible in the UIs and if not visible should be scrollable within the visible area.
The UI should be responsive and have a modern look and feel, including colors, fonts, and icons, dark mode, etc.
Data should be cleared when moving between accounts.
"""

def run():
    """
    Run the crew headlessly, no human review loop (original behavior — kept
    for training/testing/CI use cases where a human isn't in the loop).
    """
    inputs = {
        'requirements': requirements,
    }

    try:
        reset_sandbox()
        EngineeringTeam().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def run_flow():
    """
    Run the crew through the human-in-the-loop review Flow. Builds the app,
    then pauses for you to launch and test it before approving or requesting
    a targeted revision (design/backend/frontend/test) — looping until you
    approve. (ProductDevFlow.run_crew() calls reset_sandbox() itself, so no
    need to call it here.)
    """
    inputs = {
        'requirements': requirements,
    }

    try:
        ProductDevFlow().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the flow: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        EngineeringTeam().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        EngineeringTeam().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }

    try:
        EngineeringTeam().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "",
        "current_year": ""
    }

    try:
        result = EngineeringTeam().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")