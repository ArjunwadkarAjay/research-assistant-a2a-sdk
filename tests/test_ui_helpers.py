from apps.ui_helpers import parse_research_items


def test_parse_research_items_turns_bullets_into_expanders():
    summary = "Research for open source agent frameworks:\n- OpenAI Agents SDK: A flexible framework for agent workflows.\n- AutoGen: Multi-agent orchestration for Python projects."

    items = parse_research_items(summary)

    assert len(items) == 2
    assert items[0]["title"] == "OpenAI Agents SDK"
    assert items[0]["content"] == "A flexible framework for agent workflows."
    assert items[1]["title"] == "AutoGen"
