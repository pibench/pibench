Feature: Database holds domain state with serialization and hashing
    The DB provides load/dump, hashing, and JSON schema for any domain's
    data model. It's the persistence primitive.

    Scenario: Database produces a deterministic hash
        Given a fresh mock database
        And another fresh mock database
        Then both databases have the same hash

    Scenario: Hash changes after mutation
        Given a fresh mock database
        When I add a task to the database
        Then the database hash differs from a fresh database

    Scenario: Database can dump to JSON and reload identically
        Given a fresh mock database
        When I dump the database to a temp file and reload it
        Then the reloaded database has the same hash as the original

    Scenario: Database provides a JSON schema
        Given a fresh mock database
        Then the database JSON schema has a "properties" key

    Scenario: Database model validates required fields
        Given an attempt to create a database with missing fields
        Then a validation error is raised
