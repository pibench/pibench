"""TraceRecorder — deterministic trace capture with query methods.

Records tool calls with pre/post state hashes. Provides pure-function
query methods that implement the spec's check types. Immutable once
recorded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TraceEntry:
    """A single recorded tool call with state context."""

    step_index: int
    tool_name: str
    arguments: dict[str, Any]
    result_content: str
    result_error: bool
    pre_state_hash: str
    post_state_hash: str
    requestor: str
    blocked: bool = False
    db_state: dict[str, Any] | None = None

    @property
    def state_changed(self) -> bool:
        return self.pre_state_hash != self.post_state_hash


@dataclass(frozen=True)
class Message:
    """A natural-language message in the conversation."""

    role: str  # "assistant", "user", "system"
    content: str


@dataclass
class TraceRecorder:
    """Accumulates trace entries and messages. Entries are append-only."""

    _entries: list[TraceEntry] = field(default_factory=list)
    _messages: list[Message] = field(default_factory=list)

    def record(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result_content: str,
        result_error: bool,
        pre_state_hash: str,
        post_state_hash: str,
        requestor: str = "assistant",
        blocked: bool = False,
        db_state: dict[str, Any] | None = None,
    ) -> TraceEntry:
        """Record a tool call. Returns the created entry."""
        entry = TraceEntry(
            step_index=len(self._entries),
            tool_name=tool_name,
            arguments=arguments,
            result_content=result_content,
            result_error=result_error,
            pre_state_hash=pre_state_hash,
            post_state_hash=post_state_hash,
            requestor=requestor,
            blocked=blocked,
            db_state=db_state,
        )
        self._entries.append(entry)
        return entry

    def add_message(self, role: str, content: str) -> Message:
        """Record a conversation message."""
        msg = Message(role=role, content=content)
        self._messages.append(msg)
        return msg

    # --- Read-only access ---

    @property
    def entries(self) -> tuple[TraceEntry, ...]:
        """Immutable view of all trace entries."""
        return tuple(self._entries)

    @property
    def messages(self) -> tuple[Message, ...]:
        """Immutable view of all messages."""
        return tuple(self._messages)

    def next_index(self) -> int:
        """The index that will be assigned to the next entry."""
        return len(self._entries)

    # --- Check-type query methods ---

    def tool_names(self) -> list[str]:
        """All tool names called, in order."""
        return [e.tool_name for e in self._entries]

    def tool_called(self, name: str) -> bool:
        """Was this tool called at least once?"""
        return any(e.tool_name == name for e in self._entries)

    def tool_not_called(self, name: str) -> bool:
        """Was this tool never called?"""
        return not self.tool_called(name)

    def tool_called_with(self, name: str, **expected_args: Any) -> bool:
        """Was this tool called with (at least) these argument values?"""
        for e in self._entries:
            if e.tool_name == name:
                if all(
                    e.arguments.get(k) == v for k, v in expected_args.items()
                ):
                    return True
        return False

    def tool_before_tool(self, first: str, second: str) -> bool:
        """Did `first` appear before `second` in the trace?"""
        first_idx = None
        second_idx = None
        for e in self._entries:
            if e.tool_name == first and first_idx is None:
                first_idx = e.step_index
            if e.tool_name == second and second_idx is None:
                second_idx = e.step_index
        if first_idx is None or second_idx is None:
            return False
        return first_idx < second_idx

    def message_not_contains(self, pattern: str) -> bool:
        """Does no assistant message contain this pattern?"""
        for msg in self._messages:
            if msg.role == "assistant" and pattern in msg.content:
                return False
        return True

    def find_entry(self, tool_name: str) -> TraceEntry | None:
        """Find the first entry for this tool name, or None."""
        for e in self._entries:
            if e.tool_name == tool_name:
                return e
        return None
