"""COMMUNICATE evaluator — check required info strings in agent messages."""


def evaluate_communicate(communicate_info: list[str], trajectory: list[dict]) -> float:
    """Check that required information strings appear in agent messages.

    Case-insensitive substring matching. Commas stripped before comparison.
    Returns fraction of required strings found.
    """
    if not communicate_info:
        return 1.0

    agent_text = ""
    for msg in trajectory:
        if msg.get("role") == "assistant" and msg.get("content"):
            agent_text += " " + msg["content"]

    agent_text_clean = agent_text.replace(",", "").lower()

    found = 0
    for info in communicate_info:
        info_clean = info.replace(",", "").lower()
        if info_clean in agent_text_clean:
            found += 1

    return found / len(communicate_info)
