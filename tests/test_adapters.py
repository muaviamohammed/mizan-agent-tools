import json

import pytest

from mizan_agent_tools import MizanClient
from conftest import BASE


def test_langchain_tools(api):
    pytest.importorskip("langchain_core")
    from langchain_core.messages import ToolMessage
    from mizan_agent_tools.langchain import MizanVerifyCredentialTool, get_mizan_tools

    tools = get_mizan_tools(MizanClient())
    assert [t.name for t in tools] == ["mizan_verify_credential", "mizan_search_credentials", "mizan_list_datasets"]
    assert len(get_mizan_tools(include_mint_preview=True)) == 4
    verify = tools[0]
    assert "Before paying, copying, following or allocating" in verify.description
    assert set(verify.args) == {"credential_id", "sha256"}

    r = verify.invoke({"credential_id": "dsr10-flagship"})
    assert r["verified"] and r["verdict"] == "NOT_SIGNIFICANT"

    msg = verify.invoke({"args": {"credential_id": "dsr10-flagship"}, "id": "1", "name": verify.name, "type": "tool_call"})
    assert isinstance(msg, ToolMessage) and "NOT SIGNIFICANT" in msg.content

    assert tools[1].invoke({"verdict": "FAIL"})["matched"] == 1
    assert tools[2].invoke({"query": "spy"})["datasets"][0]["key"] == "spy"
    # errors come back as data, not exceptions
    assert "error" in MizanVerifyCredentialTool().invoke({})


def test_langchain_preview_tool(api):
    pytest.importorskip("langchain_core")
    from mizan_agent_tools.langchain import MizanMintPreviewTool
    api.post(f"{BASE}/x402/preview").respond(json={"preview": True, "gate_pass": True, "sharpe": 1.5})
    r = MizanMintPreviewTool().invoke({"dataset": "btc_4h", "positions": [1, 0, -1]})
    assert r["ok"] and r["gate_pass"]


def test_crewai_tools(api):
    pytest.importorskip("crewai")
    from mizan_agent_tools.crewai import MizanVerifyCredentialTool, get_mizan_tools

    tools = get_mizan_tools()
    assert len(tools) == 3 and len(get_mizan_tools(include_mint_preview=True)) == 4
    t = tools[0]
    assert "Before paying, copying, following or allocating" in t.description
    out = json.loads(t.run(credential_id="dsr10-flagship"))
    assert out["verified"] and out["verdict_raw"] == "NOT SIGNIFICANT"
    assert json.loads(tools[1].run(query="btc"))["matched"] == 2
    assert "error" in json.loads(MizanVerifyCredentialTool().run())


def test_langgraph_toolnode(api):
    pytest.importorskip("langgraph")
    from langchain_core.messages import AIMessage
    from langgraph.graph import END, START, MessagesState, StateGraph
    from langgraph.prebuilt import ToolNode
    from mizan_agent_tools.langchain import get_mizan_tools

    def model(state):
        return {"messages": [AIMessage(content="", tool_calls=[
            {"name": "mizan_verify_credential", "args": {"credential_id": "dsr10-flagship"}, "id": "c1", "type": "tool_call"}])]}

    g = StateGraph(MessagesState)
    g.add_node("model", model)
    g.add_node("tools", ToolNode(get_mizan_tools(MizanClient())))
    g.add_edge(START, "model"); g.add_edge("model", "tools"); g.add_edge("tools", END)
    out = g.compile().invoke({"messages": [("user", "verify dsr10-flagship")]})
    d = json.loads(out["messages"][-1].content)
    assert d["verified"] and d["verdict"] == "NOT_SIGNIFICANT"
