"""LangChain / LangGraph tools for MIZAN.

    pip install "mizan-agent-tools[langchain]"

    from mizan_agent_tools.langchain import get_mizan_tools
    tools = get_mizan_tools()                       # check_agent (primary) + verify + search + datasets + proven
    tools = get_mizan_tools(include_mint_preview=True)

The tools work anywhere LangChain tools work: ``model.bind_tools(tools)``,
``langchain.agents.create_agent(model, tools)``, ``langgraph.prebuilt.ToolNode(tools)``.
"""
from __future__ import annotations

from typing import Any, Optional, Type

try:
    from langchain_core.tools import BaseTool
except ImportError as e:  # pragma: no cover
    raise ImportError('LangChain adapter needs langchain-core: pip install "mizan-agent-tools[langchain]"') from e

from pydantic import BaseModel, ConfigDict, Field

from . import _text
from ._schemas import CheckAgentInput, ListDatasetsInput, ListProvenAgentsInput, MintPreviewInput, SearchCredentialsInput, VerifyCredentialInput
from .client import MizanAPIError, MizanClient

__all__ = [
    "MizanCheckAgentTool", "MizanListProvenAgentsTool", "MizanVerifyCredentialTool", "MizanSearchCredentialsTool", "MizanListDatasetsTool",
    "MizanMintPreviewTool", "get_mizan_tools",
]


def _safe(fn, *a: Any, **kw: Any) -> dict:
    try:
        return fn(*a, **kw)
    except (MizanAPIError, ValueError) as e:
        return {"error": str(e), "verified": False, "caveat": _text.CAVEAT}


class _MizanTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    client: MizanClient = Field(default_factory=MizanClient, exclude=True)


class MizanCheckAgentTool(_MizanTool):
    name: str = "mizan_check_agent"
    description: str = _text.CHECK_AGENT_DESCRIPTION
    args_schema: Type[BaseModel] = CheckAgentInput

    def _run(self, agent: str, action: str = "trusting you", **_: Any) -> dict:
        return _safe(self.client.check_agent, agent, action)


class MizanListProvenAgentsTool(_MizanTool):
    name: str = "mizan_list_proven_agents"
    description: str = _text.PROVEN_DESCRIPTION
    args_schema: Type[BaseModel] = ListProvenAgentsInput

    def _run(self, limit: int = 25, real_only: bool = True, **_: Any) -> dict:
        return _safe(self.client.list_proven_agents, limit, real_only)


class MizanVerifyCredentialTool(_MizanTool):
    name: str = "mizan_verify_credential"
    description: str = _text.VERIFY_DESCRIPTION
    args_schema: Type[BaseModel] = VerifyCredentialInput

    def _run(self, credential_id: Optional[str] = None, sha256: Optional[str] = None, **_: Any) -> dict:
        return _safe(self.client.verify_credential, credential_id, sha256)


class MizanSearchCredentialsTool(_MizanTool):
    name: str = "mizan_search_credentials"
    description: str = _text.SEARCH_DESCRIPTION
    args_schema: Type[BaseModel] = SearchCredentialsInput

    def _run(self, query: Optional[str] = None, issuer: Optional[str] = None, verdict: Optional[str] = None,
             limit: int = 10, **_: Any) -> dict:
        return _safe(self.client.list_credentials, query, issuer, verdict, limit)


class MizanListDatasetsTool(_MizanTool):
    name: str = "mizan_list_datasets"
    description: str = _text.DATASETS_DESCRIPTION
    args_schema: Type[BaseModel] = ListDatasetsInput

    def _run(self, query: Optional[str] = None, asset_class: Optional[str] = None, limit: int = 25, **_: Any) -> dict:
        return _safe(self.client.list_datasets, query, asset_class, limit)


class MizanMintPreviewTool(_MizanTool):
    name: str = "mizan_mint_preview"
    description: str = _text.PREVIEW_DESCRIPTION
    args_schema: Type[BaseModel] = MintPreviewInput

    def _run(self, dataset: str, positions: list[int], leverage_x100: int = 100, **_: Any) -> dict:
        return _safe(self.client.mint_preview, dataset=dataset, positions=positions, leverage_x100=leverage_x100)


def get_mizan_tools(client: MizanClient | None = None, include_mint_preview: bool = False) -> list[BaseTool]:
    """Return MIZAN tools sharing one client. The preview tool is opt-in because it needs a full position series."""
    c = client or MizanClient()
    tools: list[BaseTool] = [
        MizanCheckAgentTool(client=c),  # primary: call before trusting any agent
        MizanVerifyCredentialTool(client=c),
        MizanSearchCredentialsTool(client=c),
        MizanListDatasetsTool(client=c),
        MizanListProvenAgentsTool(client=c),
    ]
    if include_mint_preview:
        tools.append(MizanMintPreviewTool(client=c))
    return tools
