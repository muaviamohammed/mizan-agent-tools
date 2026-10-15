"""Pydantic argument schemas shared by the LangChain and CrewAI adapters."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CheckAgentInput(BaseModel):
    agent: str = Field(description=(
        "The agent to check: name/alias, MIZAN credential id, wallet address, ERC-8004 id, agent-card URL or sha256."))
    action: str = Field(default="trusting you", description=(
        "What you are about to do, e.g. 'copying you', 'paying you', 'allocating to you'."))


class ListProvenAgentsInput(BaseModel):
    limit: int = Field(default=25, ge=1, le=100, description="Max rows to return.")
    real_only: bool = Field(default=True, description="Only Bitcoin-confirmed, non-sandbox credentials.")


class VerifyCredentialInput(BaseModel):
    credential_id: Optional[str] = Field(
        default=None, description="MIZAN registry credential id, e.g. 'dsr10-flagship'. Give this or sha256.")
    sha256: Optional[str] = Field(
        default=None, description="Optional: the proof bundle's sha256 (64 hex) if you hold a bundle instead of an id.")


class SearchCredentialsInput(BaseModel):
    query: Optional[str] = Field(default=None, description="Text to match against credential id, alias, dataset and note.")
    issuer: Optional[str] = Field(default=None, description="Optional issuer filter (substring).")
    verdict: Optional[str] = Field(
        default=None, description="Optional verdict filter: PASS, FAIL, NOT_SIGNIFICANT, SIGNIFICANT, LEDGER_ENTRY.")
    limit: int = Field(default=10, ge=1, le=50, description="Max results to return.")


class ListDatasetsInput(BaseModel):
    query: Optional[str] = Field(default=None, description="Text to match against dataset key, label, asset or venue, e.g. 'btc'.")
    asset_class: Optional[str] = Field(default=None, description="Optional class filter, e.g. 'crypto'.")
    limit: int = Field(default=25, ge=1, le=100, description="Max results to return.")


class MintPreviewInput(BaseModel):
    dataset: str = Field(description="Canonical dataset key from the datasets tool, e.g. 'btc_4h'.")
    positions: list[int] = Field(
        description="Exactly bars-1 integers in {-1, 0, 1}: one position per bar-move on that dataset.")
    leverage_x100: int = Field(default=100, ge=10, le=1000, description="Leverage x100 (100 = 1x).")
