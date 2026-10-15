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
  Draft page: `docs/crewai/mizan-tools.mdx` (this repo). A fork branch with the page wired into
  `docs/docs.json` under Tools > Integration is prepared at
  `muaviamohammed/crewAI` branch `docs/mizan-tools` (see the report for the exact state).
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
