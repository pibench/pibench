Feature: Runner executes multi-trial simulations
    The runner takes a domain and configuration, runs k trials per task,
    collects results with evaluation rewards.

    # Spec contract 13
    Scenario: Multi-trial execution works
        Given a mock domain with 2 tasks
        And a stub agent and user that complete normally
        When I run with num_trials 3
        Then the result contains 6 simulation runs
        And each task has 3 runs

    # Spec contract 14
    Scenario: Seeds are deterministic
        Given a mock domain with 1 task
        And a deterministic stub agent
        When I run twice with seed 42
        Then both trajectories are identical

    # Spec contract 15
    Scenario: Resume skips completed work
        Given a mock domain with 3 tasks
        And a stub agent and user that complete normally
        And a save file with 2 completed runs
        When I run with resume from the save file
        Then only 1 new simulation runs
        And the final result contains all 3 runs
