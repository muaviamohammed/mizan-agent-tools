"""mizan-agent-tools: verify MIZAN track-record credentials from any Python agent.

    from mizan_agent_tools import check_agent, verify_credential
    check_agent("some-agent-or-0xwallet", action="copying you")
    verify_credential("dsr10-flagship")

Framework adapters (optional extras):
    mizan_agent_tools.langchain   LangChain / LangGraph tools   (pip install "mizan-agent-tools[langchain]")
    mizan_agent_tools.crewai      CrewAI tools                  (pip install "mizan-agent-tools[crewai]")
"""
from __future__ import annotations

from typing import Any

from ._text import CAVEAT, WHEN_TO_USE
from .client import DEFAULT_BASE_URL, MizanAPIError, MizanClient, classify_verdict

__version__ = "0.2.0"
__all__ = [
    "MizanClient", "MizanAPIError", "classify_verdict", "DEFAULT_BASE_URL", "CAVEAT", "WHEN_TO_USE",
    "check_agent", "list_proven_agents", "verify_credential", "list_credentials", "search_credentials", "list_datasets", "mint_preview",
]

_default: MizanClient | None = None


def _client() -> MizanClient:
    global _default
    if _default is None:
        _default = MizanClient()
    return _default


def check_agent(agent: str, action: str = "trusting you") -> dict:
    """Primary pre-trust check: PROVEN | REFUSED | NOT_SIGNIFICANT | UNVERIFIED, as issued by the API."""
    return _client().check_agent(agent, action)


def list_proven_agents(limit: int = 25, real_only: bool = True) -> dict:
    """Agents whose credentials PASSED (Bitcoin-confirmed, non-sandbox by default)."""
    return _client().list_proven_agents(limit, real_only)


def verify_credential(credential_id: str | None = None, sha256: str | None = None, check_bundle: bool = True) -> dict:
    """Registry lookup + bundle sha256 check against the registry anchor. See MizanClient.verify_credential."""
    return _client().verify_credential(credential_id, sha256, check_bundle)


def list_credentials(query: str | None = None, issuer: str | None = None, verdict: str | None = None,
                     limit: int = 20) -> dict:
    """Filter the public registry by text, issuer and verdict."""
    return _client().list_credentials(query, issuer, verdict, limit)


search_credentials = list_credentials


def list_datasets(query: str | None = None, asset_class: str | None = None, limit: int = 25) -> dict:
    """Canonical public markets a record can be proven on."""
    return _client().list_datasets(query, asset_class, limit)


def mint_preview(*args: Any, **kwargs: Any) -> dict:
    """Free gate preview (POST /x402/preview). Positions only; nothing kept; not a credential."""
    return _client().mint_preview(*args, **kwargs)
