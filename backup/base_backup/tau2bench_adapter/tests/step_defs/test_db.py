"""Step definitions for db.feature — database persistence and hashing."""

import json
import tempfile

import pytest
from pytest_bdd import scenarios, given, when, then

from tau2.domains.mock.data_model import MockDB
from tau2.domains.mock.utils import MOCK_DB_PATH

scenarios("../features/db.feature")


# --- Given ---


@given("a fresh mock database", target_fixture="db")
def fresh_mock_db():
    return MockDB.load(MOCK_DB_PATH)


@given("another fresh mock database", target_fixture="db2")
def another_fresh_mock_db():
    return MockDB.load(MOCK_DB_PATH)


@given("an attempt to create a database with missing fields", target_fixture="validation_error")
def db_missing_fields():
    try:
        MockDB.model_validate({"tasks": {}})
        return None
    except Exception as e:
        return e


# --- When ---


@when("I add a task to the database", target_fixture="_")
def add_task_to_db(db):
    from tau2.domains.mock.data_model import Task

    db.tasks["task_new"] = Task(
        task_id="task_new",
        title="Added task",
        status="pending",
    )


@when("I dump the database to a temp file and reload it", target_fixture="reloaded_db")
def dump_and_reload(db):
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        path = f.name
    db.dump(path)
    return MockDB.load(path)


# --- Then ---


@then("both databases have the same hash")
def same_db_hash(db, db2):
    assert db.get_hash() == db2.get_hash()


@then("the database hash differs from a fresh database")
def hash_differs_from_fresh(db):
    fresh = MockDB.load(MOCK_DB_PATH)
    assert db.get_hash() != fresh.get_hash()


@then("the reloaded database has the same hash as the original")
def reloaded_hash_matches(db, reloaded_db):
    assert db.get_hash() == reloaded_db.get_hash()


@then('the database JSON schema has a "properties" key')
def db_has_json_schema(db):
    schema = db.get_json_schema()
    assert "properties" in schema, f"Schema missing 'properties': {schema.keys()}"


@then("a validation error is raised")
def validation_error_raised(validation_error):
    assert validation_error is not None, "Expected a validation error but got None"
