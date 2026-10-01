# 7–10 Minute Demo Script

## 0:00–1:00 — Introduction

Explain that Xena is an agentic HR assistant combining policy RAG, MCP tools and synthetic employee data. Point out the chat UI and health indicator.

## 1:00–2:00 — Architecture

Show the architecture in `design-and-evaluation.md`. Explain the web app → orchestrator → MCP client → MCP server → RAG/mock data → LLM flow.

## 2:00–4:00 — Demo 1: Remote work

Use:

> EMP001 wants to work remotely from another UK region for six weeks. Is this allowed, what checks are required, and what should they do next?

Point to:

1. `lookup_employee_profile` and the `EMP001` argument.
2. `search_policy_documents` and retrieved policy sources.
3. `check_policy_compliance` and its conservative result.
4. Citations and the final answer.

Emphasise that the result is guidance, not automatic approval.

## 4:00–6:00 — Demo 2: PTO

Use:

> EMP001 wants to take 3 days of PTO next week. Check their balance, the PTO policy, approval requirements, and draft the next-step message.

Point to:

1. employee lookup;
2. PTO balance;
3. PTO policy retrieval;
4. `draft_hr_email`;
5. draft-only safety behaviour;
6. citations and trace.

## 6:00–7:00 — CI/CD

Show the GitHub Actions workflow and explain that it installs dependencies, builds the RAG index, runs tests and performs an import check.

## 7:00–8:00 — Evaluation

Show the 24-question evaluation set and the generated metrics: groundedness, citation accuracy, tool selection, workflow completion, safety and p50/p95 latency. Mention the retrieval-k ablation.

## 8:00–9:00 — Deployment and limitations

Show the deployed URL and `/health`. Explain free-tier cold starts. Mention that all employee records and actions are synthetic/mock.

## 9:00–10:00 — Close

Summarise that the application demonstrates RAG, MCP discovery/calls, structured data use, two multi-step workflows, citations, safety guardrails, CI/CD, deployment and evaluation.
