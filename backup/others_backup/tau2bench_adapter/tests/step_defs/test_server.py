"""Step definitions for server.feature — HTTP server for environment tools."""

from pytest_bdd import scenarios, given, when, then, parsers

from fastapi.testclient import TestClient
from tau2.domains.mock.data_model import MockDB
from tau2.domains.mock.tools import MockTools
from tau2.domains.mock.utils import MOCK_DB_PATH, MOCK_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.environment.server import EnvironmentServer

scenarios("../features/server.feature")


# --- Given ---


@given("a fresh environment server", target_fixture="server")
def fresh_server():
    db = MockDB.load(MOCK_DB_PATH)
    tools = MockTools(db)
    with open(MOCK_POLICY_PATH, "r") as fp:
        policy = fp.read()
    env = Environment(domain_name="mock", policy=policy, tools=tools)
    srv = EnvironmentServer(env)
    srv._client = TestClient(srv.app)
    return srv


# --- When ---


@when(parsers.parse('I POST to "{path}" with no body'), target_fixture="response")
def post_no_body(server, path):
    return server._client.post(path, json={})


@when(
    parsers.parse('I POST to "{path}" with user_id "{user_id}" and title "{title}"'),
    target_fixture="response",
)
def post_with_args(server, path, user_id, title):
    return server._client.post(
        path, json={"user_id": user_id, "title": title, "description": ""}
    )


# --- Then ---


@then("the server has a FastAPI app")
def server_has_app(server):
    assert server.app is not None


@then(parsers.parse('the app has a POST route for "{path}"'))
def app_has_route(server, path):
    routes = [r.path for r in server.app.routes]
    assert path in routes, f"Route '{path}' not found. Available: {routes}"


@then(parsers.parse("the response status is {status:d}"))
def response_status(response, status):
    assert response.status_code == status, (
        f"Expected {status} but got {response.status_code}: {response.text}"
    )
