Feature: Runner executes multi-trial simulations with parallel execution
    The runner takes a domain, tasks, and configuration, then runs k
    trials per task using a thread pool. Results are collected, saved
    incrementally, and support resume.

    # --- Single trial ---

    Scenario: Single trial returns one simulation run per task
        Given a mock domain with 2 tasks
        And a stub agent and user that complete normally
        When I run with num_trials 1
        Then the result contains 2 simulation runs
        And each run has a different task_id

    # --- Multi-trial (k-runs) ---

    Scenario: Multiple trials return k runs per task
        Given a mock domain with 1 task
        And a stub agent and user that complete normally
        When I run with num_trials 4
        Then the result contains 4 simulation runs
        And all runs have the same task_id
        And each run has a different trial number

    Scenario: Each trial gets a unique seed
        Given a mock domain with 1 task
        And a stub agent and user that complete normally
        When I run with num_trials 4 and seed 42
        Then each simulation run has a different seed
        And the seeds are deterministic given the base seed

    Scenario: Same base seed produces same set of trial seeds
        Given a mock domain with 1 task
        And a stub agent and user that complete normally
        When I run twice with num_trials 4 and seed 42
        Then both runs produce identical trial seeds

    # --- Reproducibility ---

    Scenario: Deterministic agent with same seed produces same trajectory
        Given a mock domain with 1 task
        And a deterministic stub agent
        When I run twice with seed 42
        Then both trajectories are identical

    # --- Parallel execution ---

    Scenario: Concurrent trials all complete
        Given a mock domain with 3 tasks
        And a stub agent and user that complete normally
        When I run with num_trials 2 and max_concurrency 4
        Then the result contains 6 simulation runs

    Scenario: Max concurrency limits parallel threads
        Given a mock domain with 10 tasks
        And a stub agent and user that complete normally
        When I run with num_trials 1 and max_concurrency 2
        Then at most 2 simulations run simultaneously

    # --- Result collection ---

    Scenario: Result contains metadata about the run configuration
        Given a mock domain with 1 task
        And a stub agent and user that complete normally
        When I run with num_trials 1
        Then the result contains agent model name
        And the result contains user model name
        And the result contains the domain name

    Scenario: Abnormal termination gets reward 0.0
        Given a mock domain with 1 task
        And a stub agent that always errors
        When I run with num_trials 1
        Then the simulation run has reward 0.0

    Scenario: Normal completion gets evaluated reward
        Given a mock domain with 1 task and expected actions
        And a stub agent that performs the expected actions then stops
        When I run with num_trials 1
        Then the simulation run has reward greater than 0.0

    # --- Incremental save ---

    Scenario: Results are saved incrementally as runs complete
        Given a mock domain with 3 tasks
        And a stub agent and user that complete normally
        And a save path
        When I run with num_trials 1
        Then the save file exists after the run
        And the save file contains all 3 simulation runs

    # --- Resume ---

    Scenario: Resume skips already-completed runs
        Given a mock domain with 3 tasks
        And a save file with 2 completed runs
        And a stub agent and user that complete normally
        When I run with resume from the save file
        Then only 1 new simulation runs
        And the final result contains all 3 runs

    # --- Task filtering ---

    Scenario: Running specific task IDs only runs those tasks
        Given a mock domain with 5 tasks
        And a stub agent and user that complete normally
        When I run with task_ids "task_0,task_2"
        Then the result contains 2 simulation runs
        And the task IDs are "task_0" and "task_2"
