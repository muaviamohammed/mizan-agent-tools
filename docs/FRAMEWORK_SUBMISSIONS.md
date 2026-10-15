# Framework submissions: status and next steps

Checked 2026-10-15 via the GitHub API. Nothing below has been opened or filed.

## CrewAI

- `crewAIInc/crewAI-tools` is archived (last push 2025-10-23). Tools now live in the monorepo
  `crewAIInc/crewAI` under `lib/crewai-tools/`, docs under `docs/edge/en/` (Mintlify, nav in
  `docs/docs.json`). `AGENTS.md` asks contributors to sync translations (`ar`, `ko`, `pt-BR`)
  after English doc edits.
- Third-party *code* tool PRs pile up open (e.g. #7748, #7713, #7704, #7660 open for weeks).
  Docs-only pages for externally hosted tools do get merged (e.g. #5563 You.com MCP pages).
- Chosen route: a docs-only page that points to this package and the remote MCP server.
  Draft page: `docs/crewai/mizan-tools.mdx` (this repo). Prepared fork branch:
  https://github.com/muaviamohammed/crewAI/tree/docs/mizan-tools (English + ar/ko/pt-BR):
  new `docs/edge/en/tools/integration/mizantools.mdx`, nav entry in `docs/docs.json`
  (Tools > Integrations), and a card in `docs/edge/en/tools/integration/overview.mdx`.
  No PR has been opened.
- To open: publish to PyPI first, add the `ar`/`ko`/`pt-BR` translations, then open the PR from
  the fork branch.

## LangChain

- LangChain lists external packages instead of hosting their code. Process: publish on PyPI, then
  file the "Integration listing" issue in `langchain-ai/docs`
  (`.github/ISSUE_TEMPLATE/06-integration-submission.yml`); a maintainer labels it
  `integration-run` and a docs PR is generated from the fields.
- Draft page (template-conformant) and suggested form values: `docs/langchain_integration.md`.
- Naming note: LangChain's convention for partner packages is `langchain-<name>`. This package
  is framework-neutral (`mizan-agent-tools[langchain]`), which the form accepts ("installable
  name without extras"). A thin `langchain-mizan` alias package is optional, not required.

### Draft PR body (CrewAI)

Title: `docs(tools): add MIZAN track-record verification tools page`

> Docs-only. Adds a page under Tools > Integrations for MIZAN, which issues zero-knowledge
> track-record credentials for trading strategies and agents. The page shows two routes:
> the external `mizan-agent-tools` package (CrewAI `BaseTool` subclasses, no API key) and
> MIZAN's remote MCP server via `MCPServerHTTP`. No new code in crewAI.
>
> Test plan: `docs/docs.json` is valid JSON; page renders with `mintlify dev`; examples
> were run against crewai 1.15 (tools construct on an `Agent`, `tool.run(...)` returns JSON).
