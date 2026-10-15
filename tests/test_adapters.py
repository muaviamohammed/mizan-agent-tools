import json

import pytest

from mizan_agent_tools import MizanClient
from conftest import BASE


def test_langchain_tools(api):
    pytest.importorskip("langchain_core")
    from langchain_core.messages import ToolMessage
    from mizan_agent_tools.langchain import MizanVerifyCredentialTool, get_mizan_tools

    tools = get_mizan_tools(MizanClient())
    assert [t.name for t in tools] == ["mizan_check_agent", "mizan_verify_credential", "mizan_search_credentials",
                                       "mizan_list_datasets", "mizan_list_proven_agents"]
    assert len(get_mizan_tools(include_mint_preview=True)) == 6
    assert "BEFORE following, copying, paying, hiring or allocating" in tools[0].description
    verify = tools[1]
    assert "Before paying, copying, following or allocating" in verify.description
    assert set(verify.args) == {"credential_id", "sha256"}

    r = verify.invoke({"credential_id": "dsr10-flagship"})
    assert r["verified"] and r["verdict"] == "NOT_SIGNIFICANT"

    msg = verify.invoke({"args": {"credential_id": "dsr10-flagship"}, "id": "1", "name": verify.name, "type": "tool_call"})
    assert isinstance(msg, ToolMessage) and "NOT SIGNIFICANT" in msg.content

    assert tools[2].invoke({"verdict": "FAIL"})["matched"] == 1
    assert tools[3].invoke({"query": "spy"})["datasets"][0]["key"] == "spy"
    chk = tools[0].invoke({"agent": "0xabc123", "action": "copying you"})
    assert chk["status"] == "UNVERIFIED" and "forward_to_counterparty" in chk
    assert tools[4].invoke({"limit": 5})["count"] == 1
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
    assert len(tools) == 5 and len(get_mizan_tools(include_mint_preview=True)) == 6
    assert tools[0].name == "MIZAN Check Agent"
    assert json.loads(tools[0].run(agent="v12-btc-trend-4h"))["status"] == "PROVEN"
    assert json.loads(tools[4].run(limit=5))["proven"][0]["verdict"] == "PASS"
    assert "error" in json.loads(tools[0].run(agent=" "))
    t = tools[1]
    assert "Before paying, copying, following or allocating" in t.description
    out = json.loads(t.run(credential_id="dsr10-flagship"))
    assert out["verified"] and out["verdict_raw"] == "NOT SIGNIFICANT"
    assert json.loads(tools[2].run(query="btc"))["matched"] == 2
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
