"""Opt-in live checks against the real MIZAN API: pytest -m live"""
import json

import pytest

from mizan_agent_tools import MizanClient

pytestmark = pytest.mark.live


def _some_id(c):
    ids = [x["id"] for x in c.registry()["credentials"]]
    return "dsr10-flagship" if "dsr10-flagship" in ids else ids[0]


def test_live_verify_real_credential():
    c = MizanClient()
    r = c.verify_credential(_some_id(c))
    assert r["found"] and r["hash_match"] is True and r["verified"] is True
    assert r["verdict_raw"] and "not a forecast" in r["caveat"]


def test_live_langchain_and_crewai_tools():
    c = MizanClient()
    cid = _some_id(c)
    try:
        from mizan_agent_tools.langchain import get_mizan_tools as lc
        assert lc(c)[1].invoke({"credential_id": cid})["verified"] is True
    except ImportError:
        pass
    try:
        from mizan_agent_tools.crewai import get_mizan_tools as cr
        assert json.loads(cr(c)[1].run(credential_id=cid))["verified"] is True
    except ImportError:
        pass


def test_live_check_agent():
    c = MizanClient()
    assert c.check_agent("0xabc123", action="copying you")["status"] == "UNVERIFIED"
    r = c.check_agent("zkml12")
    assert r["found"] and r["status"] in ("PROVEN", "REFUSED", "NOT_SIGNIFICANT")


def test_live_list_proven_agents():
    r = MizanClient().list_proven_agents(limit=5, real_only=True)
    assert isinstance(r["proven"], list) and r["caveat"]
    assert all(row.get("verdict") == "PASS" for row in r["proven"])
