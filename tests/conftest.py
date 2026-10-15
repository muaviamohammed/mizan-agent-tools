import hashlib

import pytest
import respx

BASE = "https://studio.mizan.market"
BUNDLE = b"fake-stark-bundle-bytes"
BUNDLE_SHA = hashlib.sha256(BUNDLE).hexdigest()


def make_registry():
    return {
        "count": 3,
        "registry_root": "ab" * 32,
        "credentials": [
            {
                "id": "dsr10-flagship", "alias": "Flagship DSR", "issuer": "MIZAN",
                "dataset": "BTC 4h OHLC 2020-26", "verdict": "NOT SIGNIFICANT", "kind": "dsr",
                "era": "guest v10 · dafad185…", "engine_era": "v10", "engine_status": "superseded",
                "anchor": {"sha256": BUNDLE_SHA, "ots_state": "confirmed"},
                "disclosed_metrics": {"deflated_sharpe": 0.6779, "n_trials": 10},
                "links": {"bundle": "https://mizan.market/verify/files/dsr.bundle", "verify": "https://mizan.market/verify#dsr"},
                "verify_command": "./verifier dsr.bundle btc_4h.csv",
            },
            {
                "id": "pass-btc-trend-4h", "alias": "BTC trend 4h", "issuer": "MIZAN Studio",
                "dataset": "BTC 4h", "verdict": "PASS ✓ — Sharpe≥1.20", "kind": "gate", "sandbox": True,
                "anchor": {"sha256": "00" * 32},
                "links": {"bundle": "https://mizan.market/verify/files/pass.bundle"},
            },
            {
                "id": "honest-fail-spy", "alias": "SPY trend", "issuer": "MIZAN",
                "dataset": "SPY daily", "verdict": "FAIL · SharpeTooLow — published anyway", "kind": "honest_fail",
                "anchor": {"sha256": BUNDLE_SHA},
                "links": {"bundle": "http://insecure.example/x.bundle"},
            },
        ],
    }


DATASETS = {
    "max_positions": 13000,
    "datasets": [
        {"key": "btc_4h", "label": "BTC · 4h", "asset": "BTC", "cls": "crypto", "bars": 12917, "interval": "4h",
         "venue": "Binance", "first": "2020", "last": "2026", "sha256": "aa", "public": True, "align_group": "crypto_4h"},
        {"key": "spy", "label": "SPY daily", "asset": "SPY", "cls": "us_etf", "bars": 7184, "interval": "1d",
         "venue": "US", "first": "1997", "last": "2026", "sha256": "bb", "public": True},
        {"key": "hidden", "label": "Withdrawn", "public": False},
    ],
}


CHECK_UNVERIFIED = {
    "query": "0xabc123", "status": "UNVERIFIED", "found": False, "matches": [],
    "summary": "No MIZAN credential matches this agent. Its claimed performance is unproven, which is not the same as false.",
    "advice": "Treat performance claims from this agent as unverified until it holds a credential.",
    "forward_to_counterparty": "I checked your track record with MIZAN before copying you and found no credential.",
    "how_to_prove": {"docs": "https://mizan.market/skill/"},
    "caveat": "A credential is a seal on a past record, not a forecast.",
}
CHECK_PROVEN = {
    "query": "v12-btc-trend-4h", "status": "PROVEN", "found": True, "match": "exact", "count": 1,
    "matches": [{"id": "v12-btc-trend-4h", "verdict": "PASS", "verdict_raw": "PASS", "issuer": "MIZAN",
                 "bitcoin_confirmed": True, "engine_era": "v12"}],
    "summary": "At least one credential for this agent PASSED the gate.",
    "caveat": "A credential is a seal on a past record, not a forecast.",
}
PROVEN = {
    "count": 1, "proven": [{"id": "v12-btc-trend-4h", "verdict": "PASS", "issuer": "MIZAN", "bitcoin_confirmed": True}],
    "filter": "PASS verdicts, Bitcoin-confirmed only",
    "disclosure": "Every credential so far was minted by MIZAN itself while open testing lasts; issuer is shown on each row.",
    "caveat": "A credential is a seal on a past record, not a forecast.",
}


def _check(request):
    import httpx
    q = request.url.params.get("q")
    return httpx.Response(200, json=CHECK_PROVEN if q == "v12-btc-trend-4h" else {**CHECK_UNVERIFIED, "query": q})


@pytest.fixture
def api():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/registry").respond(json=make_registry())
        mock.get("https://mizan.market/verify/files/dsr.bundle").respond(content=BUNDLE)
        mock.get("https://mizan.market/verify/files/pass.bundle").respond(content=b"tampered")
        mock.get(f"{BASE}/api/blackbox-datasets").respond(json=DATASETS)
        mock.get(f"{BASE}/api/agents/check").mock(side_effect=_check)
        mock.get(f"{BASE}/api/agents/proven").respond(json=PROVEN)
        yield mock
