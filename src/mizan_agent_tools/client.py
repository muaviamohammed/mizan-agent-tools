"""Small synchronous client for the public MIZAN studio API.

Endpoints used (all public, no account):
    GET  {base}/api/registry               list of credentials + registry Merkle root
    GET  {bundle url from the registry}    proof bundle, sha256-checked against the registry anchor
    GET  {base}/api/blackbox-datasets      canonical markets a record can be proven on
    POST {base}/x402/preview               free gate preview (positions only; rate-limited per IP)

Nothing here sends a model, weights, code or prompt.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import time
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import httpx

from ._text import CAVEAT

__all__ = ["MizanClient", "MizanAPIError", "classify_verdict", "DEFAULT_BASE_URL"]

DEFAULT_BASE_URL = "https://studio.mizan.market"
REGISTRY_PAGE = "https://mizan.market/registry/"
VERIFY_PAGE = "https://mizan.market/verify/"
OFFLINE_VERIFIER = "https://github.com/muaviamohammed/mizan-verify/releases"
_VERSION = "0.1.0"


class MizanAPIError(RuntimeError):
    """Raised when the MIZAN API cannot be reached or returns an unusable response."""

    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def classify_verdict(raw: str | None) -> str:
    """Map the registry's human verdict string to a stable class.

    Returns one of PASS, NOT_SIGNIFICANT, SIGNIFICANT, FAIL, or LEDGER_ENTRY (anything else,
    e.g. a label-seal or PBO entry). The raw string is always returned alongside; this is
    only a convenience for branching, never a replacement.
    """
    v = (raw or "").strip().upper()
    for key in ("PASS", "NOT SIGNIFICANT", "SIGNIFICANT", "FAIL"):
        if v.startswith(key):
            return key.replace(" ", "_")
    return "LEDGER_ENTRY"


def _norm(s: Any) -> str:
    return str(s or "").casefold()


class MizanClient:
    """Thin, honest client. Every result says what was checked locally and what is a registry claim."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
        registry_ttl: float = 60.0,
        transport: httpx.BaseTransport | None = None,
        http_client: httpx.Client | None = None,
    ):
        self.base_url = (base_url or os.environ.get("MIZAN_STUDIO_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.registry_ttl = registry_ttl
        self._http = http_client or httpx.Client(
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
            headers={"User-Agent": f"mizan-agent-tools/{_VERSION} (+https://github.com/muaviamohammed/mizan-agent-tools)"},
        )
        self._registry: dict | None = None
        self._registry_at = 0.0

    # ------------------------------------------------------------------ http
    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "MizanClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _get_json(self, url: str) -> Any:
        try:
            r = self._http.get(url)
        except httpx.HTTPError as e:
            raise MizanAPIError(f"could not reach {url}: {e}") from e
        if r.status_code >= 400:
            raise MizanAPIError(f"GET {url} returned HTTP {r.status_code}", r.status_code, r.text[:500])
        try:
            return r.json()
        except ValueError as e:
            raise MizanAPIError(f"GET {url} did not return JSON") from e

    # -------------------------------------------------------------- registry
    def registry(self, refresh: bool = False) -> dict:
        """Raw registry JSON (cached for ``registry_ttl`` seconds)."""
        now = time.monotonic()
        if refresh or self._registry is None or now - self._registry_at > self.registry_ttl:
            data = self._get_json(f"{self.base_url}/api/registry")
            if not isinstance(data, dict) or not isinstance(data.get("credentials"), list):
                raise MizanAPIError("registry response has no 'credentials' list", payload=data)
            self._registry, self._registry_at = data, now
        return self._registry

    def _find(self, credential_id: str | None, sha256: str | None) -> dict | None:
        creds = self.registry()["credentials"]
        cid = (credential_id or "").strip()
        sh = (sha256 or "").strip().lower()
        for c in creds:
            if cid and c.get("id") == cid:
                return c
            if sh and ((c.get("anchor") or {}).get("sha256") or "").lower() == sh:
                return c
        return None

    def _abs(self, link: Any) -> Any:
        """Registry links may be relative to the studio (e.g. '/credential/<id>/bundle')."""
        if isinstance(link, str) and link.startswith("/"):
            return urljoin(self.base_url + "/", link.lstrip("/"))
        return link

    def _links(self, c: dict) -> dict:
        return {k: self._abs(v) for k, v in (c.get("links") or {}).items()}

    def _summary(self, c: dict) -> dict:
        links = self._links(c)
        return {
            "id": c.get("id"),
            "alias": c.get("alias"),
            "issuer": c.get("issuer"),
            "verdict": classify_verdict(c.get("verdict")),
            "verdict_raw": c.get("verdict"),
            "kind": c.get("kind"),
            "era": c.get("era"),
            "engine_status": c.get("engine_status"),
            "dataset": c.get("dataset"),
            "minted_utc": c.get("minted_utc"),
            "sandbox": bool(c.get("sandbox")),
            "link": links.get("credential") or links.get("verify") or REGISTRY_PAGE,
        }

    def list_credentials(
        self,
        query: str | None = None,
        issuer: str | None = None,
        verdict: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Filter the public registry.

        ``query`` matches (case-insensitive substring) id, alias, dataset and note.
        ``issuer`` matches the issuer field. ``verdict`` matches either the verdict class
        (PASS, FAIL, NOT_SIGNIFICANT, SIGNIFICANT, LEDGER_ENTRY) or a substring of the raw verdict.
        """
        reg = self.registry()
        q, iss, ver = _norm(query), _norm(issuer), _norm(verdict).replace("_", " ")
        out = []
        for c in reg["credentials"]:
            if q and not any(q in _norm(c.get(k)) for k in ("id", "alias", "dataset", "note")):
                continue
            if iss and iss not in _norm(c.get("issuer")):
                continue
            if ver:
                cls = classify_verdict(c.get("verdict")).replace("_", " ").casefold()
                if ver != cls and ver not in _norm(c.get("verdict")):
                    continue
            out.append(self._summary(c))
        limit = max(1, min(int(limit or 20), 200))
        return {
            "total_in_registry": len(reg["credentials"]),
            "matched": len(out),
            "credentials": out[:limit],
            "truncated": len(out) > limit,
            "registry_root": reg.get("registry_root"),
            "registry_page": REGISTRY_PAGE,
            "note": "Registry listings include passes and fails. Use the verify tool on an id for the hash check.",
        }

    # ---------------------------------------------------------------- verify
    def verify_credential(
        self,
        credential_id: str | None = None,
        sha256: str | None = None,
        check_bundle: bool = True,
    ) -> dict:
        """Look a credential up and (by default) check the bundle's sha256 against the registry anchor.

        ``verified`` is True only when the credential is in the registry AND the downloaded bundle
        hashes to the anchored sha256. ``verified`` says the record is intact and listed; it does
        not say the record passed. Read ``verdict`` for that.
        """
        if not (credential_id or sha256):
            raise ValueError("pass credential_id or sha256")
        c = self._find(credential_id, sha256)
        reg = self.registry()
        if c is None:
            return {
                "found": False,
                "verified": False,
                "verdict": "UNVERIFIED",
                "verdict_raw": None,
                "query": {"credential_id": credential_id, "sha256": sha256},
                "reason": "no such credential in the public MIZAN registry",
                "interpretation": "No MIZAN credential was found. Treat the claimed performance as unproven.",
                "registry_root": reg.get("registry_root"),
                "caveat": CAVEAT,
            }
        anchor = c.get("anchor") or {}
        links = self._links(c)
        bundle_url = links.get("bundle") or ""
        expected = (anchor.get("sha256") or "").lower()
        res: dict[str, Any] = {
            "found": True,
            **self._summary(c),
            "engine_era": c.get("engine_era"),
            "engine_image_id": c.get("engine_image_id"),
            "disclosed_metrics": c.get("disclosed_metrics") or {},
            "anchor": {"sha256": anchor.get("sha256"), "ots_state": anchor.get("ots_state"),
                       "tsa_time_utc": anchor.get("tsa_time_utc")},
            "registry_leaf": c.get("registry_leaf"),
            "registry_root": reg.get("registry_root"),
            "verify_command": c.get("verify_command"),
            "links": {**links, "registry_page": REGISTRY_PAGE, "verify_page": VERIFY_PAGE},
            "checks": {
                "registry_lookup": True,
                "bundle_sha256_match": None,
                "stark_reverified_locally": False,
            },
            "hash_match": None,
            "verified": False,
            "caveat": CAVEAT,
        }
        if c.get("sandbox"):
            res["sandbox_note"] = "This entry is flagged sandbox in the registry."
        if c.get("engine_status") == "superseded":
            res["era_note"] = "Minted under an earlier engine era; it still verifies under that era's verifier."
        if not check_bundle:
            res["reason"] = "bundle hash check skipped by caller"
            res["interpretation"] = self._interpret(res)
            return res
        if not expected:
            res["reason"] = ("the registry publishes no anchored sha256 for this entry, so this client cannot "
                             "hash-check its bundle; integrity is unconfirmed (the offline verifier can still check the proof)")
            res["interpretation"] = self._interpret(res)
            return res
        if urlparse(bundle_url).scheme != "https":
            res.update(hash_match=False, reason="registry entry has no https bundle URL to check against its anchor")
            res["checks"]["bundle_sha256_match"] = False
            res["interpretation"] = self._interpret(res)
            return res
        try:
            r = self._http.get(bundle_url)
        except httpx.HTTPError as e:
            res["reason"] = f"bundle not downloadable: {e}"
            res["interpretation"] = self._interpret(res)
            return res
        if r.status_code >= 400:
            res["reason"] = f"bundle URL returned HTTP {r.status_code}"
            res["interpretation"] = self._interpret(res)
            return res
        got = hashlib.sha256(r.content).hexdigest()
        match = got == expected
        res.update(hash_match=match, bundle_sha256=got, bundle_bytes=len(r.content), verified=match)
        res["checks"]["bundle_sha256_match"] = match
        if not match:
            res["verdict"] = "UNVERIFIED"
            res["reason"] = "bundle sha256 does not match the registry anchor: do not trust this record"
        res["interpretation"] = self._interpret(res)
        return res

    @staticmethod
    def _interpret(res: dict) -> str:
        if res.get("hash_match") is False:
            return "Integrity check FAILED or not possible. Do not treat this record as verified."
        if res.get("hash_match") is None:
            return (f"Listed in the registry with verdict '{res.get('verdict_raw')}', but the bundle hash "
                    f"was not confirmed ({res.get('reason', 'not checked')}). Do not treat it as verified.")
        v = res.get("verdict")
        base = "Bundle hash matches the registry anchor. "
        if v == "PASS":
            return base + "Verdict as issued: PASS (the record cleared the gate on its committed data and costs)."
        if v == "SIGNIFICANT":
            return base + f"Verdict as issued: {res.get('verdict_raw')}."
        if v in ("FAIL", "NOT_SIGNIFICANT"):
            return base + (f"Verdict as issued: {res.get('verdict_raw')}. The record is intact as "
                           "published, but it did not clear the bar; do not treat it as proven performance.")
        return base + f"This is a ledger entry ({res.get('verdict_raw')}), not a pass/fail gate verdict."

    # -------------------------------------------------------------- datasets
    def list_datasets(self, query: str | None = None, asset_class: str | None = None, limit: int = 25) -> dict:
        data = self._get_json(f"{self.base_url}/api/blackbox-datasets")
        rows = data.get("datasets") or []
        q, cls = _norm(query), _norm(asset_class)
        keep = ("key", "label", "asset", "cls", "bars", "interval", "venue", "first", "last", "sha256", "align_group")
        out = []
        for d in rows:
            if not d.get("public", True):
                continue
            if q and not any(q in _norm(d.get(k)) for k in ("key", "label", "asset", "venue")):
                continue
            if cls and cls != _norm(d.get("cls")):
                continue
            out.append({k: d.get(k) for k in keep})
        limit = max(1, min(int(limit or 25), 500))
        return {
            "total": len(rows),
            "matched": len(out),
            "datasets": out[:limit],
            "truncated": len(out) > limit,
            "max_positions": data.get("max_positions"),
            "csv_url_template": f"{self.base_url}/api/catalog/{{key}}.csv",
            "note": "Positions for a dataset must have exactly bars-1 entries (one per bar-move).",
        }

    # ---------------------------------------------------------------- preview
    def mint_preview(
        self,
        dataset: str | None = None,
        positions: Iterable[int] | Iterable[Iterable[int]] = (),
        model_id: str = "preview",
        leverage_x100: int = 100,
        datasets: list[str] | None = None,
        gross_cap_x100: int | None = None,
        model_salt: str | None = None,
        track_salt: str | None = None,
    ) -> dict:
        """POST /x402/preview: free gate preview, positions only, nothing kept, not a credential.

        Single market: ``dataset`` + ``positions`` (ints in {-1,0,1}, exactly bars-1).
        Book (multi-asset): ``datasets`` + ``positions`` as rows of K signed leverages x100 + ``gross_cap_x100``.
        Salts are random throwaways here because a preview keeps nothing.
        """
        pos = [list(map(int, p)) if isinstance(p, (list, tuple)) else int(p) for p in positions]
        if not pos:
            raise ValueError("positions must be a non-empty list")
        body: dict[str, Any] = {
            "positions": pos,
            "model_id": model_id,
            "model_salt": model_salt or secrets.token_hex(32),
            "track_salt": track_salt or secrets.token_hex(32),
            "leverage_x100": int(leverage_x100),
            "preview_only": True,
        }
        if datasets:
            body["datasets"] = list(datasets)
            if gross_cap_x100 is not None:
                body["gross_cap_x100"] = int(gross_cap_x100)
        else:
            if not dataset:
                raise ValueError("pass dataset (or datasets for a book)")
            body["dataset"] = dataset
        url = f"{self.base_url}/x402/preview"
        try:
            r = self._http.post(url, json=body, timeout=max(self._http.timeout.read or 30, 180))
        except httpx.HTTPError as e:
            raise MizanAPIError(f"could not reach {url}: {e}") from e
        try:
            payload = r.json()
        except ValueError:
            payload = {"raw": r.text[:500]}
        note = "Dev-mode preview: nothing is kept and this is not a credential. Minting a credential is a separate step."
        if r.status_code >= 400:
            return {"ok": False, "status_code": r.status_code,
                    "error": (payload or {}).get("error") if isinstance(payload, dict) else str(payload),
                    "detail": payload, "note": note}
        return {"ok": True, "status_code": r.status_code, **(payload if isinstance(payload, dict) else {"result": payload}),
                "note": note}
