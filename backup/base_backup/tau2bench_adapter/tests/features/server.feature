Feature: Environment server exposes tools as HTTP endpoints
    The server wraps an Environment and creates REST endpoints for each
    tool, allowing agents to interact via HTTP.

    Scenario: Server creates a FastAPI app
        Given a fresh environment server
        Then the server has a FastAPI app

    Scenario: Server creates routes for agent tools
        Given a fresh environment server
        Then the app has a POST route for "/tools/get_users"
        And the app has a POST route for "/tools/create_task"

    Scenario: Agent tool endpoint returns a result
        Given a fresh environment server
        When I POST to "/tools/get_users" with no body
        Then the response status is 200

    Scenario: Agent tool endpoint with arguments returns a result
        Given a fresh environment server
        When I POST to "/tools/create_task" with user_id "user_1" and title "Test"
        Then the response status is 200

    Scenario: Agent tool endpoint with bad user returns error status
        Given a fresh environment server
        When I POST to "/tools/create_task" with user_id "nonexistent" and title "Bad"
        Then the response status is 400
