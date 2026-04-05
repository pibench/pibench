Feature: Orchestrator hooks
    A plugin system that lets external code observe orchestrator
    events without modifying pi-bench core behavior.

    Scenario: Plugin registers for named hook points
        Given a hook registry with valid hook points
        When a plugin registers callables for "on_init" and "after_tool_call"
        Then the registry contains both hooks

    Scenario: Simulation with no plugins produces identical results
        Given a task and domain with no plugins registered
        When I run the simulation twice with the same seed
        Then both runs produce the same trajectory and reward

    Scenario: Registering for a non-existent hook raises an error
        Given a hook registry with valid hook points
        When a plugin registers for "on_banana"
        Then a registration error is raised immediately

    Scenario: All registered callables are called at the hook point
        Given two plugins registered for "after_agent_call"
        When the simulation runs and the agent responds
        Then both plugin callables have been invoked

    Scenario: Hook callables receive a read-only state snapshot
        Given a plugin registered for "after_tool_call" that modifies its context
        When a tool call occurs during simulation
        Then the modification does not affect the orchestrator state

    Scenario: Plugin exception does not crash the simulation
        Given a plugin registered for "after_agent_call" that raises an exception
        When the simulation runs
        Then the simulation completes normally despite the plugin error

    Scenario: Hook invocation order matches registration order
        Given three plugins registered for "on_done" in order A B C
        When the simulation completes
        Then the plugins were invoked in order A B C

    Scenario: Plugin cannot modify trajectory or routing
        Given a plugin registered for "after_agent_call" that attempts to alter trajectory
        When the simulation runs to completion
        Then the trajectory is identical to a run without the plugin

    Scenario: pi-bench core has no import of the plugin package
        Given the pi_bench source directory
        When I scan all Python files for imports of pi_plugins
        Then no imports are found
