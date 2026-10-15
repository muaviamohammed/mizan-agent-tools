---
title: "MIZAN integration"
description: "Integrate with the MIZAN track-record verification tools using LangChain Python."
---

<!--
Draft for the LangChain docs (langchain-ai/docs), following
src/oss/python/integrations/tools/TEMPLATE.mdx. Target path if accepted:
src/oss/python/integrations/tools/mizan.mdx

How LangChain lists third-party integrations today (checked 2026-10-15): publish the package on
PyPI first, then open the "Integration listing" issue form in langchain-ai/docs
(.github/ISSUE_TEMPLATE/06-integration-submission.yml). A maintainer applies the
`integration-run` label and a docs PR is generated from the form fields. Suggested field values
are at the bottom of this file. Do not file before `pip install mizan-agent-tools` works.
-->

This guide provides a quick overview for getting started with the MIZAN [tools](/oss/langchain/tools). MIZAN issues zero-knowledge (STARK) credentials for trading track records and publishes passes and fails in a public registry. These tools let an agent look up a credential and check it before paying, copying, following or allocating to a trading agent or strategy. For the full field reference, see the [package README](https://github.com/muaviamohammed/mizan-agent-tools#readme).

## Overview

### Details

| Class | Package | Serializable | JS support | Downloads | Version |
| :--- | :--- | :---: | :---: | :---: | :---: |
| [MizanCheckAgentTool](https://github.com/muaviamohammed/mizan-agent-tools/blob/main/src/mizan_agent_tools/langchain.py) | [mizan-agent-tools](https://pypi.org/project/mizan-agent-tools/) | ❌ | ❌ | ![PyPI - Downloads](https://img.shields.io/pypi/dm/mizan-agent-tools?style=flat-square&label=%20) | ![PyPI - Version](https://img.shields.io/pypi/v/mizan-agent-tools?style=flat-square&label=%20) |

### Features

- `mizan_check_agent` (primary): call before following, copying, paying, hiring or allocating to any agent or wallet that claims returns. Takes a name/alias, credential id, wallet address, ERC-8004 id, agent-card URL or sha256, plus the action about to be taken. Returns `status` PROVEN, REFUSED, NOT_SIGNIFICANT or UNVERIFIED with the matching credentials, a summary and a caveat. UNVERIFIED means unproven, not false; it includes a `forward_to_counterparty` message the caller may pass on.
- `mizan_list_proven_agents`: credentials that passed the gate (Bitcoin-confirmed, non-sandbox by default), with the issuer on each row.
- `mizan_verify_credential`: looks a credential up by id (or bundle sha256) in the public registry, downloads the proof bundle and checks its sha256 against the registry anchor. Returns the verdict exactly as issued (PASS, FAIL, NOT SIGNIFICANT, ...), `verified` / `hash_match` flags, engine era, dataset, any owner-disclosed metrics, links, and a caveat that a credential is a seal on a past record, not a forecast.
- `mizan_search_credentials`: filters the registry by alias, issuer or verdict to find a credential id.
- `mizan_list_datasets`: lists the canonical public markets a record can be proven on.
- `mizan_mint_preview` (opt-in): free, rate-limited gate preview of your own position series. Positions only; nothing is kept; not a credential.
- No API key. All calls go to public endpoints.

---

## Setup

The tools need no account and no API key. Verification reads the public registry at `https://studio.mizan.market/api/registry`.

### Credentials

None required.

It's also helpful (but not needed) to set up LangSmith for best-in-class observability/<Tooltip tip="Log each step of a model's execution to debug and improve it">tracing</Tooltip> of your tool calls. To enable automated tracing, set your [LangSmith](/langsmith/observability) API key:

```python Enable tracing icon="flask"
import getpass
import os

os.environ["LANGSMITH_API_KEY"] = getpass.getpass("Enter your LangSmith API key: ")
os.environ["LANGSMITH_TRACING"] = "true"
```

### Installation

The MIZAN tools live in the `mizan-agent-tools` package, with the LangChain adapter behind an extra:

<CodeGroup>
    ```python pip
    pip install -U "mizan-agent-tools[langchain]"
    ```
    ```python uv
    uv add "mizan-agent-tools[langchain]"
    ```
</CodeGroup>

---

## Instantiation

```python Initialize tool instance icon="robot"
from mizan_agent_tools.langchain import MizanCheckAgentTool, MizanVerifyCredentialTool, get_mizan_tools

tool = MizanCheckAgentTool()
verify = MizanVerifyCredentialTool()
tools = get_mizan_tools()  # check_agent first, then verify, search, datasets, proven; one shared HTTP client
```

---

## Invocation

### Directly

The check tool takes `agent` (anything that identifies it) and `action` (what you are about to do).

```python Call tool icon="rocket"
result = tool.invoke({"agent": "0xabc123", "action": "copying you"})
result["status"], result["summary"]   # "UNVERIFIED", "...unproven, which is not the same as false."
```

For a credential you will rely on, the verify tool takes `credential_id` (a registry id) or `sha256` (the proof bundle's hash) and checks the bundle hash against the registry anchor:

```python Verify a credential icon="shield-check"
result = verify.invoke({"credential_id": "dsr10-flagship"})
result["verified"], result["verdict_raw"], result["interpretation"]
```

`verified` is `True` only when the credential is in the registry and the downloaded bundle hashes to the anchored sha256. It says the record is intact and listed. It does not say the record passed; read `verdict` for that.

### As a ToolCall

We can also invoke the tool with a model-generated `ToolCall`, in which case a @[`ToolMessage`] will be returned:

```python ToolCall icon="briefcase"
model_generated_tool_call = {
    "args": {"agent": "v12-btc-trend-4h", "action": "allocating to you"},
    "id": "1",
    "name": tool.name,
    "type": "tool_call",
}
tool.invoke(model_generated_tool_call)
```

### Within an agent

```python Agent with tool icon="robot"
# pip install -qU "langchain[anthropic]" to call the model
from langchain.agents import create_agent

agent = create_agent(
    model="claude-sonnet-4-6",
    tools=get_mizan_tools(),
    system_prompt=(
        "Before recommending that anyone follow, copy, pay, hire or allocate to a trading agent, "
        "call mizan_check_agent and report the status exactly. UNVERIFIED means unproven, not false."
    ),
)

agent.invoke(
    {"messages": [{"role": "user", "content": "Should I copy the bot whose credential is v12-btc-trend-4h?"}]}
)
```

---

## What a credential does and does not show

- A credential shows that a record was computed as claimed from committed positions on a committed public dataset with committed costs, and how it scored against the gate. It is not a forecast and not investment advice.
- Where a credential carries a trial count, it counts strategy versions committed to MIZAN, not ideas tried elsewhere.
- These tools check registry membership and the bundle hash. They do not re-run the STARK proof; the offline [`mizan-verify`](https://github.com/muaviamohammed/mizan-verify/releases) binary does that.
- At the time of writing, every credential in the registry was minted by MIZAN itself.

---

## API reference

For all fields and options, see the [mizan-agent-tools README](https://github.com/muaviamohammed/mizan-agent-tools#readme).

<!--
Suggested "Integration listing" issue form values (langchain-ai/docs):
  Display or class name:   MizanCheckAgentTool
  Language:                Python
  Component type:          tools
  PyPI package name:       mizan-agent-tools
  npm package name:        (blank)
  Docs URL:                https://github.com/muaviamohammed/mizan-agent-tools#readme
                           (or a hosted copy of this page, e.g. https://mizan.market/skill/langchain)
  Source repository:       muaviamohammed/mizan-agent-tools
  Short provider description (factual, no marketing):
      Tools to check trading agents against the MIZAN registry and hash-check its zero-knowledge track-record credentials.
-->
