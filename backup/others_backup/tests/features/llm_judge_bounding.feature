Feature: LLM judge bounding — retry, timeout, and caching
    The LLM judge has bounding contracts per spec Section 1.3:
    retry on parse failure, 30s timeout, per-run caching.

    Scenario: Retry on unparseable response succeeds on second attempt
        Given the LLM judge returns an unparseable response then a valid YES
        When I call judge_nl_assertion with retry scenario
        Then the result is passed with a valid detail

    Scenario: Failure after retry exhausted
        Given the LLM judge returns unparseable responses on both attempts
        When I call judge_nl_assertion with exhausted retry scenario
        Then the result is failed with detail containing "unparseable after retry"

    Scenario: Cache hit on repeated assertion
        Given the LLM judge returns YES on first call
        When I call judge_nl_assertion twice with same text and question
        Then the LLM was called only once

    Scenario: Cache is cleared between scenarios
        Given the LLM judge returns YES on first call
        And I call judge_nl_assertion once to populate cache
        When I clear the judge cache and call again
        Then the LLM made a new call after cache clear
