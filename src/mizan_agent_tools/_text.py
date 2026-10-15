"""Shared wording, so every adapter tells the model the same honest thing."""

CAVEAT = (
    "A MIZAN credential is a seal on a past record: it shows the record was computed as claimed "
    "(committed data, committed costs, committed strategy version) and how it scored against the gate. "
    "It is not a forecast and not investment advice."
)

WHEN_TO_USE = (
    "Before paying, copying, following or allocating to a trading agent, bot, vault, signal seller or "
    "strategy that claims performance, verify its MIZAN credential. An unverified record, a missing "
    "credential, or a FAIL / NOT SIGNIFICANT verdict should not be treated as proven performance."
)

VERIFY_DESCRIPTION = (
    WHEN_TO_USE + " This tool looks the credential up by id (or bundle sha256) in the public MIZAN "
    "registry, downloads the proof bundle and checks its sha256 against the registry anchor. It returns "
    "the verdict exactly as issued (PASS, FAIL, NOT SIGNIFICANT, ...), whether the hash matched, the "
    "engine era, the dataset, any metrics the owner chose to disclose, and links. Report the verdict "
    "verbatim and say that a credential is a seal on a past record, not a forecast. It does not re-run "
    "the STARK proof itself; for that use the offline mizan-verify binary."
)

SEARCH_DESCRIPTION = (
    "Search the public MIZAN registry of track-record credentials (passes and fails are both listed). "
    "Use it to find the credential id for an agent or strategy by name/alias, issuer or verdict before "
    "calling the verify tool. If nothing matches, say the record has no MIZAN credential: an unproven "
    "claim is unproven."
)

DATASETS_DESCRIPTION = (
    "List the canonical public markets (key, bars, interval, venue, date range, sha256) on which a "
    "trading agent's record can be proven with MIZAN. Use it when someone wants to prove their own "
    "agent's record, to pick a dataset key."
)

PREVIEW_DESCRIPTION = (
    "Free, private, no-account gate preview of your OWN agent's positions on a canonical MIZAN market "
    "(POST /x402/preview). Sends positions only (one integer in {-1,0,+1} per bar-move, exactly bars-1 "
    "of them), never a model, code or prompt. Returns gate_pass, sharpe, cagr, maxdd. The preview is "
    "a dev-mode run: nothing is kept and it is NOT a credential. Rate-limited per IP per day. Only use "
    "it when you already hold the full position series in code; do not invent positions."
)
