"""Adapter: maps pi_bench.domains.mock interface to tau2's mock domain."""

from tau2.domains.mock.data_model import MockDB
from tau2.domains.mock.tools import MockTools
from tau2.domains.mock.utils import MOCK_DB_PATH, MOCK_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool


def get_environment(policy: str | None = None) -> Environment:
    """Create a fresh mock environment, optionally with a custom policy."""
    db = MockDB.load(MOCK_DB_PATH)
    tools = MockTools(db)

    if policy is None:
        with open(MOCK_POLICY_PATH, "r") as fp:
            policy = fp.read()

    return Environment(
        domain_name="mock",
        policy=policy,
        tools=tools,
    )


class UserOnlyTools(ToolKitBase):
    """A minimal toolkit with a user-only tool for testing requestor routing."""

    db: MockDB

    def __init__(self, db: MockDB) -> None:
        super().__init__(db)

    @is_tool(ToolType.READ)
    def user_only_tool(self) -> str:
        """A tool only available to user requestors."""
        return "user only result"

    @is_tool(ToolType.READ)
    def get_users(self) -> list:
        """Get all users — user-side copy for routing tests."""
        return list(self.db.users.values())


class UserOnlyToolsNoOverlap(ToolKitBase):
    """User tools without overlapping names — required for solo mode."""

    db: MockDB

    def __init__(self, db: MockDB) -> None:
        super().__init__(db)

    @is_tool(ToolType.READ)
    def user_only_tool(self) -> str:
        """A tool only available to user requestors."""
        return "user only result"


def get_initial_db() -> MockDB:
    """Get a fresh copy of the initial mock database."""
    return MockDB.load(MOCK_DB_PATH)


def get_environment_with_user_tools() -> Environment:
    """Create a mock environment that has both agent and user tool collections."""
    db = MockDB.load(MOCK_DB_PATH)
    agent_tools = MockTools(db)
    user_tools = UserOnlyTools(db)

    with open(MOCK_POLICY_PATH, "r") as fp:
        policy = fp.read()

    return Environment(
        domain_name="mock",
        policy=policy,
        tools=agent_tools,
        user_tools=user_tools,
    )
