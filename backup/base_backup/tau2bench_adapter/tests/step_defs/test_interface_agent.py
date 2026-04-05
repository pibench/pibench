"""Step definitions for interface_agent.feature — LLM agentic loop."""

import os

import pytest
from pytest_bdd import scenarios, given, when, then

from tau2.domains.mock.data_model import MockDB
from tau2.domains.mock.tools import MockTools
from tau2.domains.mock.utils import MOCK_DB_PATH, MOCK_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.environment.utils.interface_agent import InterfaceAgent

scenarios("../features/interface_agent.feature")


# Check if we have an API key for LLM tests
HAS_API_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))
skip_no_key = pytest.mark.skipif(not HAS_API_KEY, reason="ANTHROPIC_API_KEY not set")


def _make_env():
    db = MockDB.load(MOCK_DB_PATH)
    tools = MockTools(db)
    with open(MOCK_POLICY_PATH, "r") as fp:
        policy = fp.read()
    return Environment(domain_name="mock", policy=policy, tools=tools)


# --- Given ---


@given("a fresh interface agent", target_fixture="agent")
def fresh_agent():
    env = _make_env()
    return InterfaceAgent(
        environment=env,
        llm="anthropic/claude-haiku-4-5-20251001",
        llm_args={"max_tokens": 512},
    )


# --- When ---


@when('the agent receives message "How many users are there?"', target_fixture="agent_response")
@skip_no_key
def agent_how_many_users(agent):
    response, history = agent.respond("How many users are there?")
    return {"response": response, "history": history}


@when('the agent receives message "List all users"', target_fixture="agent_response")
@skip_no_key
def agent_list_users(agent):
    response, history = agent.respond("List all users")
    return {"response": response, "history": history}


@when("I set the agent seed to 42", target_fixture="_")
def set_seed(agent):
    agent.set_seed(42)


# --- Then ---


@then("the agent returns a non-empty response")
@skip_no_key
def agent_has_response(agent_response):
    response = agent_response["response"]
    assert response.content and len(response.content.strip()) > 0


@then("the agent response mentions user data")
@skip_no_key
def agent_mentions_users(agent_response):
    content = agent_response["response"].content.lower()
    assert "user" in content or "test" in content, (
        f"Expected user data in response: {content}"
    )


@then("the message history has more than 1 entry")
@skip_no_key
def history_has_entries(agent_response):
    history = agent_response["history"]
    assert len(history) > 1, f"Expected >1 messages, got {len(history)}"


@then("the seed is set without error")
def seed_set(agent):
    assert agent.llm_args.get("seed") == 42
