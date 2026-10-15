import json

import httpx
import pytest

from mizan_agent_tools import CAVEAT, MizanAPIError, MizanClient, classify_verdict
from conftest import BASE, BUNDLE_SHA


@pytest.mark.parametrize("raw,cls", [
    ("PASS", "PASS"), ("PASS ✓ — Sharpe≥1.20", "PASS"), ("NOT SIGNIFICANT", "NOT_SIGNIFICANT"),
    ("SIGNIFICANT · 95%", "SIGNIFICANT"), ("FAIL — published anyway", "FAIL"),
    ("LABELS SEALED", "LEDGER_ENTRY"), (None, "LEDGER_ENTRY"),
])
def test_classify_verdict(raw, cls):
    assert classify_verdict(raw) == cls


def test_verify_hash_match(api):
    r = MizanClient().verify_credential("dsr10-flagship")
    assert r["found"] and r["verified"] and r["hash_match"]
    assert r["verdict"] == "NOT_SIGNIFICANT" and r["verdict_raw"] == "NOT SIGNIFICANT"
    assert r["bundle_sha256"] == BUNDLE_SHA
    assert r["checks"] == {"registry_lookup": True, "bundle_sha256_match": True, "stark_reverified_locally": False}
    assert r["disclosed_metrics"]["n_trials"] == 10
    assert r["era"].startswith("guest v10") and r["engine_status"] == "superseded" and "era_note" in r
    assert r["caveat"] == CAVEAT and "not a forecast" in r["caveat"]
    assert "did not clear the bar" in r["interpretation"]
    assert r["links"]["registry_page"].startswith("https://mizan.market/registry")
    json.dumps(r)  # LLM-safe


def test_verify_by_sha256(api):
    r = MizanClient().verify_credential(sha256=BUNDLE_SHA.upper())
    assert r["id"] == "dsr10-flagship" and r["verified"]


def test_verify_hash_mismatch_is_unverified(api):
    r = MizanClient().verify_credential("pass-btc-trend-4h")
    assert r["found"] and r["hash_match"] is False and r["verified"] is False
    assert r["verdict"] == "UNVERIFIED" and r["verdict_raw"].startswith("PASS")
    assert r["sandbox"] is True and "sandbox_note" in r
    assert "do not trust" in r["reason"]


def test_verify_rejects_non_https_bundle(api):
    r = MizanClient().verify_credential("honest-fail-spy")
    assert r["hash_match"] is False and not r["verified"]
    assert not api.calls or all("insecure.example" not in str(c.request.url) for c in api.calls)


def test_verify_not_found(api):
    r = MizanClient().verify_credential("nope")
    assert r == {**r, "found": False, "verified": False, "verdict": "UNVERIFIED"}
    assert "unproven" in r["interpretation"]


def test_verify_skip_bundle(api):
    r = MizanClient().verify_credential("dsr10-flagship", check_bundle=False)
    assert r["hash_match"] is None and r["verified"] is False
    assert "not confirmed" in r["interpretation"]


def test_verify_bundle_404(api):
    api.get("https://mizan.market/verify/files/dsr.bundle").respond(404)
    r = MizanClient().verify_credential("dsr10-flagship")
    assert r["verified"] is False and "404" in r["reason"]


def test_verify_requires_an_argument(api):
    with pytest.raises(ValueError):
        MizanClient().verify_credential()


def test_registry_error_raises():
    import respx
    with respx.mock() as m:
        m.get(f"{BASE}/api/registry").respond(503)
        with pytest.raises(MizanAPIError) as ei:
            MizanClient().registry()
        assert ei.value.status_code == 503


def test_registry_network_error_raises():
    import respx
    with respx.mock() as m:
        m.get(f"{BASE}/api/registry").mock(side_effect=httpx.ConnectError("down"))
        with pytest.raises(MizanAPIError):
            MizanClient().registry()


def test_registry_is_cached(api):
    c = MizanClient()
    c.list_credentials(); c.list_credentials(); c.verify_credential("dsr10-flagship", check_bundle=False)
    assert api.routes[0].call_count == 1
    c.registry(refresh=True)
    assert api.routes[0].call_count == 2


def test_base_url_env(monkeypatch):
    monkeypatch.setenv("MIZAN_STUDIO_URL", "https://example.test/")
    assert MizanClient().base_url == "https://example.test"


def test_list_credentials_filters(api):
    c = MizanClient()
    assert c.list_credentials()["matched"] == 3
    assert [x["id"] for x in c.list_credentials(query="btc")["credentials"]] == ["dsr10-flagship", "pass-btc-trend-4h"]
    assert [x["id"] for x in c.list_credentials(issuer="studio")["credentials"]] == ["pass-btc-trend-4h"]
    assert [x["id"] for x in c.list_credentials(verdict="FAIL")["credentials"]] == ["honest-fail-spy"]
    assert [x["id"] for x in c.list_credentials(verdict="not_significant")["credentials"]] == ["dsr10-flagship"]
    r = c.list_credentials(limit=1)
    assert r["truncated"] and len(r["credentials"]) == 1 and r["total_in_registry"] == 3


def test_list_datasets(api):
    c = MizanClient()
    r = c.list_datasets()
    assert r["matched"] == 2 and r["max_positions"] == 13000
    assert [d["key"] for d in c.list_datasets(query="btc")["datasets"]] == ["btc_4h"]
    assert [d["key"] for d in c.list_datasets(asset_class="us_etf")["datasets"]] == ["spy"]


def test_mint_preview_body_and_result(api):
    route = api.post(f"{BASE}/x402/preview").respond(
        json={"preview": True, "gate_pass": False, "sharpe": 0.4, "cagr": 3.1, "maxdd": 21.0, "n_periods": 4})
    r = MizanClient().mint_preview("btc_4h", [0, 1, -1, 1])
    body = json.loads(route.calls[0].request.content)
    assert body["dataset"] == "btc_4h" and body["positions"] == [0, 1, -1, 1] and body["preview_only"] is True
    assert len(body["model_salt"]) == 64 and len(body["track_salt"]) == 64
    assert set(body) == {"dataset", "positions", "model_id", "model_salt", "track_salt", "leverage_x100", "preview_only"}
    assert r["ok"] and r["gate_pass"] is False and "not a credential" in r["note"]


def test_mint_preview_book_body(api):
    route = api.post(f"{BASE}/x402/preview").respond(json={"preview": True, "gate_pass": True})
    MizanClient().mint_preview(datasets=["btc_4h", "eth_4h"], positions=[[50, -50], [100, 0]], gross_cap_x100=100)
    body = json.loads(route.calls[0].request.content)
    assert body["datasets"] == ["btc_4h", "eth_4h"] and body["positions"] == [[50, -50], [100, 0]]
    assert body["gross_cap_x100"] == 100 and "dataset" not in body


def test_mint_preview_rate_limited(api):
    api.post(f"{BASE}/x402/preview").respond(429, json={"error": "preview limit reached for today"})
    r = MizanClient().mint_preview("btc_4h", [1])
    assert r["ok"] is False and r["status_code"] == 429 and "limit" in r["error"]


def test_mint_preview_validation():
    c = MizanClient()
    with pytest.raises(ValueError):
        c.mint_preview("btc_4h", [])
    with pytest.raises(ValueError):
        c.mint_preview(None, [1])


def test_module_level_functions(api):
    import mizan_agent_tools as m
    m._default = None
    assert m.verify_credential("dsr10-flagship")["verified"]
    assert m.search_credentials("spy")["matched"] == 1
    assert m.list_datasets("btc")["matched"] == 1


def _with_extra(api, *entries):
    from conftest import make_registry
    reg = make_registry()
    reg["credentials"].extend(entries)
    api.get(f"{BASE}/api/registry").respond(json=reg)


def test_relative_bundle_link_resolves_against_studio(api):
    from conftest import BUNDLE
    _with_extra(api, {"id": "bb-rel", "verdict": "PASS", "anchor": {"sha256": BUNDLE_SHA},
                      "links": {"bundle": "/api/blackbox-submission/rel/bundle", "credential": "/credential/bb-rel"}})
    api.get(f"{BASE}/api/blackbox-submission/rel/bundle").respond(content=BUNDLE)
    r = MizanClient().verify_credential("bb-rel")
    assert r["verified"] and r["verdict"] == "PASS"
    assert r["links"]["bundle"] == f"{BASE}/api/blackbox-submission/rel/bundle"
    assert r["link"] == f"{BASE}/credential/bb-rel"


def test_entry_without_anchor_is_unconfirmed_not_mismatch(api):
    _with_extra(api, {"id": "mzn_noanchor", "verdict": "PASS", "links": {"bundle": "/credential/mzn_noanchor/bundle"}})
    r = MizanClient().verify_credential("mzn_noanchor")
    assert r["found"] and r["verified"] is False and r["hash_match"] is None
    assert r["checks"]["bundle_sha256_match"] is None
    assert r["verdict"] == "PASS"  # registry verdict reported as issued, but not confirmed
    assert "no anchored sha256" in r["reason"] and "Do not treat it as verified" in r["interpretation"]


def test_check_agent_unverified_sends_query_and_action(api):
    r = MizanClient().check_agent("0xabc123", action="copying you")
    req = [c.request for c in api.calls if c.request.url.path == "/api/agents/check"][-1]
    assert req.url.params["q"] == "0xabc123" and req.url.params["action"] == "copying you"
    assert r["status"] == "UNVERIFIED" and r["found"] is False
    assert "not the same as false" in r["summary"] and r["forward_to_counterparty"]
    assert r["checks"]["bundle_sha256_match"] is None and r["checks"]["stark_reverified_locally"] is False


def test_check_agent_proven_passthrough(api):
    r = MizanClient().check_agent("v12-btc-trend-4h")
    req = [c.request for c in api.calls if c.request.url.path == "/api/agents/check"][-1]
    assert req.url.params["action"] == "trusting you"
    assert r["status"] == "PROVEN" and r["matches"][0]["id"] == "v12-btc-trend-4h"
    assert "forward_to_counterparty" not in r and "not a forecast" in r["caveat"]


def test_check_agent_validation_and_errors(api):
    with pytest.raises(ValueError):
        MizanClient().check_agent("  ")
    api.get(f"{BASE}/api/agents/check").respond(500)
    with pytest.raises(MizanAPIError):
        MizanClient().check_agent("x")


def test_list_proven_agents(api):
    r = MizanClient().list_proven_agents(limit=5, real_only=False)
    req = [c.request for c in api.calls if c.request.url.path == "/api/agents/proven"][-1]
    assert req.url.params["limit"] == "5" and req.url.params["real_only"] == "false"
    assert r["count"] == 1 and "minted by MIZAN itself" in r["disclosure"]


def test_module_level_agent_functions(api):
    import mizan_agent_tools as m
    m._default = None
    assert m.check_agent("0xabc123")["status"] == "UNVERIFIED"
    assert m.list_proven_agents()["proven"]
