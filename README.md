# mizan-agent-tools

Check a trading agent's track record before you trust it.

`mizan-agent-tools` gives LangChain, LangGraph and CrewAI agents a built-in way to look up and
check a [MIZAN](https://mizan.market) track-record credential before paying, copying, following
or allocating to a trading agent, bot, vault or strategy. A MIZAN credential is a zero-knowledge
proof (STARK) that a record was computed as claimed on committed data under committed costs,
without revealing the strategy. Passes and fails are published side by side.

The rule the tools teach the model: **check before you trust. No credential (UNVERIFIED), a hash
mismatch, or a REFUSED / FAIL / NOT SIGNIFICANT verdict means the claimed performance is not proven.
Unproven is not the same as false.**

```
pip install mizan-agent-tools                 # core client (httpx + pydantic)
pip install "mizan-agent-tools[langchain]"    # + LangChain tools
pip install "mizan-agent-tools[langgraph]"    # + LangGraph
pip install "mizan-agent-tools[crewai]"       # + CrewAI tools
```

Python 3.10+. No API key needed: verification uses public endpoints only.

## Plain Python

Start with `check_agent`. It is the call to make before following, copying, paying, hiring or
allocating to any agent or wallet that claims returns.

```python
from mizan_agent_tools import check_agent, list_proven_agents

r = check_agent("0xabc123", action="copying you")   # name/alias, credential id, wallet, ERC-8004 id, agent-card URL or sha256
r["status"]                    # "UNVERIFIED" (also: PROVEN, REFUSED, NOT_SIGNIFICANT), exactly as the API issued it
r["summary"]                   # "...Its claimed performance is unproven, which is not the same as false."
r["forward_to_counterparty"]   # only when UNVERIFIED: a message you may pass to the agent so it can prove its record

check_agent("zkml12")["status"]          # "REFUSED" (partial match on alias; matches[] lists each credential)
list_proven_agents(limit=25, real_only=True)   # PASS verdicts, Bitcoin-confirmed, non-sandbox; with a disclosure line
```

`check_agent` returns the API response as issued (`query`, `status`, `found`, `match`, `matches[]` with
`id, alias, verdict, verdict_raw, kind, issuer, dataset, minted_utc, bitcoin_confirmed, engine_era, page`,
`summary`, `advice`, `forward_to_counterparty`, `how_to_prove`, `caveat`) plus a `checks` block. The match is done
server-side; it does not download or hash-check a bundle. For a match you will rely on, follow up with
`verify_credential` on its id:

```python
from mizan_agent_tools import verify_credential, search_credentials

r = verify_credential("dsr10-flagship")
r["verified"]       # True: in the registry AND the bundle's sha256 matches the registry anchor
r["verdict"]        # "NOT_SIGNIFICANT" (class) ; r["verdict_raw"] = "NOT SIGNIFICANT" (as issued)
r["interpretation"] # plain-English reading, e.g. "...did not clear the bar; do not treat it as proven performance."
r["caveat"]         # "A MIZAN credential is a seal on a past record ... not a forecast ..."

search_credentials("btc", verdict="PASS")    # find ids by alias / issuer / verdict
```

What `verify_credential` returns (all JSON-serialisable):

| field | meaning |
|---|---|
| `found` | the id or sha256 is in the public registry |
| `verified` | `found` **and** the downloaded bundle hashes to the registry's anchored sha256 |
| `hash_match` | `True` / `False` / `None` (not checkable: no anchor published, or bundle unreachable) |
| `checks` | what this call actually checked: `registry_lookup`, `bundle_sha256_match`, `stark_reverified_locally` (always `False` here) |
| `verdict`, `verdict_raw` | class (`PASS`, `FAIL`, `NOT_SIGNIFICANT`, `SIGNIFICANT`, `LEDGER_ENTRY`, or `UNVERIFIED`) and the exact registry string |
| `era`, `engine_era`, `engine_status`, `engine_image_id` | which engine era minted it; superseded eras still verify under their own verifier |
| `dataset`, `minted_utc`, `issuer`, `kind`, `sandbox` | registry facts, passed through |
| `disclosed_metrics` | only the metrics the owner chose to disclose; often empty |
| `anchor`, `registry_root`, `registry_leaf`, `verify_command`, `links` | material for independent checking |
| `interpretation`, `caveat` | honest plain-English reading; the caveat is always present |

Other calls: `list_datasets(query)` lists the canonical markets a record can be proven on, and
`mint_preview(dataset, positions)` runs the free, rate-limited gate preview
(`POST /x402/preview`, positions only, nothing kept, not a credential).

## LangChain

```python
from mizan_agent_tools.langchain import get_mizan_tools

tools = get_mizan_tools()
# [mizan_check_agent (primary), mizan_verify_credential, mizan_search_credentials,
#  mizan_list_datasets, mizan_list_proven_agents]
check = tools[0]
check.invoke({"agent": "0xabc123", "action": "copying you"})   # -> status UNVERIFIED
tools[1].invoke({"credential_id": "dsr10-flagship"})           # bundle hash check

model_with_tools = model.bind_tools(tools)   # any tool-calling chat model
```

`get_mizan_tools(include_mint_preview=True)` adds `mizan_mint_preview`. It is opt-in because it
needs the full position series (thousands of integers), which should come from your code, not
from the model.

## LangGraph

```python
# pip install "mizan-agent-tools[langgraph]" "langchain[anthropic]"
from langchain.agents import create_agent          # LangChain v1 agents run on LangGraph
from mizan_agent_tools.langchain import get_mizan_tools

agent = create_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=get_mizan_tools(),
    system_prompt=(
        "You help users decide whether to follow trading agents. Before recommending that anyone "
        "follow, copy, pay, hire or allocate to an agent, call mizan_check_agent and report the status "
        "exactly. UNVERIFIED means unproven, not false. Hash-check any credential you rely on with "
        "mizan_verify_credential."
    ),
)
agent.invoke({"messages": [{"role": "user", "content": "Should I copy the agent v12-btc-trend-4h?"}]})
```

On older stacks `langgraph.prebuilt.create_react_agent(model, tools)` works the same way, and the
tools drop into a hand-built graph via `langgraph.prebuilt.ToolNode(get_mizan_tools())`.

## CrewAI

```python
from crewai import Agent, Crew, Task
from mizan_agent_tools.crewai import get_mizan_tools

due_diligence = Agent(
    role="Allocation due-diligence analyst",
    goal="Only recommend trading agents whose track record is verified",
    backstory="You never vouch for a record from a screenshot. You check the MIZAN credential.",
    tools=get_mizan_tools(),
)
task = Task(
    description="Before we copy the bot 'v12-btc-trend-4h', check it with MIZAN, hash-check any credential you rely on, and advise.",
    expected_output="Status as issued, whether the hash matched, and a one-paragraph recommendation.",
    agent=due_diligence,
)
Crew(agents=[due_diligence], tasks=[task]).kickoff()
```

`get_mizan_tools()` returns `MIZAN Check Agent` first, then verify, search, datasets and proven-agents
tools. CrewAI tools return a JSON string with the same fields as above.

## MCP alternative

If your framework speaks MCP, the same verify tool is served at `https://studio.mizan.market/mcp`
(streamable HTTP) and as a stdio server, see https://github.com/muaviamohammed/mizan-mcp.

## Honest boundary

What a credential shows:

- The record was computed as claimed from the committed positions on a committed public dataset,
  with the committed costs, and scored against the gate. The STARK proof can be checked offline
  with the `mizan-verify` binary without trusting MIZAN.
- Where the credential carries a trial count (deflated-Sharpe entries), it counts the strategy
  versions **committed to MIZAN**. It cannot count ideas that were tried and never committed.

What it does not show:

- It is not a forecast. A PASS is a seal on a past record, not a promise about future returns,
  and it is not investment advice.
- It does not prove live execution quality. Fill-dependent and HFT strategies are not credentialed.
- This package checks registry membership and the bundle's sha256 against the registry anchor.
  It does **not** re-run the STARK verification (`checks.stark_reverified_locally` is always
  `False`). For that, run the offline verifier from
  https://github.com/muaviamohammed/mizan-verify/releases with the entry's `verify_command`.
- Some registry entries publish no anchored sha256; for those `verified` is `False` and
  `hash_match` is `None`, meaning "not checkable by this client", not "tampered".

Who issued what: as of this release, every credential in the public registry was minted by MIZAN
itself (including entries made through the self-serve studio). There are no third-party issuers
listed yet, and this package does not imply any endorsement by LangChain, CrewAI or anyone else.

## Configuration

- `MIZAN_STUDIO_URL` overrides the API base (default `https://studio.mizan.market`).
- `MizanClient(timeout=30, registry_ttl=60)` caches the registry for 60 s per client.

## Development

```
pip install -e ".[test,langchain,langgraph,crewai]"
pytest              # unit tests, HTTP mocked
pytest -m live      # opt-in: hits the real registry and verifies a real credential
```

## Links

Standard (VTR-1): https://mizan.market/standard-spec ·
Registry: https://mizan.market/registry/ ·
Verify page: https://mizan.market/verify/ ·
Agent skill: https://mizan.market/skill/

MIT licensed.
