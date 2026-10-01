# Project Requirements Matrix

| Brief requirement | Implementation | Verification |
|---|---|---|
| Local reproducible environment | `requirements.txt`, `.env.example`, README | `pip install -r requirements.txt` |
| Secrets in environment variables | `.env`, `config.py`, `.gitignore` | no API key in repo |
| 5–20 policy files | 10 Markdown policy files | `policies/` |
| Two source formats supported | `document_loader.py` supports Markdown/TXT, HTML, PDF | unit/manual ingestion |
| Deterministic chunking | section-aware + 900/120 overlap | `rag_pipeline.py` |
| Embedding model | SentenceTransformer MiniLM | `config.py` |
| Lightweight vector DB | Chroma persistent collection | `rag_pipeline.py` |
| Top-k RAG | default k=4, configurable | `search_policy_documents` |
| Citation metadata | document, section, source file, snippet, chunk ID | `/chat` response |
| Out-of-corpus guardrail | no-evidence response redirects to HR | orchestrator |
| Multi-document question | remote/security/compliance policy set | evaluation Q09/Q10/Q24 |
| Agent orchestration | planner + orchestrator | `agent/` |
| 2 multi-step workflows | remote work + PTO | UI demo buttons |
| Operational trace | tool names, arguments, outputs, sources | UI expandable trace |
| Failure handling | MCP error, missing employee, missing evidence | tests + orchestrator |
| Safe actions | draft-only email and mock ticket | MCP tools + safety rules |
| 5+ MCP tools | 8 tools | MCP discovery test |
| Actual MCP calls | MCP stdio client/server | `tests/test_smoke.py` |
| Web chat | Flask UI | `/` |
| `/chat` endpoint | implemented | `app.py` |
| `/health` endpoint | implemented | `app.py` |
| Reproducible demo tasks | `/api/demo-tasks` + UI buttons | UI |
| Free-tier deployment | Render config + single service | `render.yaml`, `deployed.md` |
| CI/CD | GitHub Actions on push/PR | `.github/workflows/ci.yml` |
| MCP CI test | discovery + employee tool call | `tests/test_smoke.py` |
| 20–30 evaluation cases | 24 questions | `evaluation/questions.json` |
| Answer metrics | groundedness + citation accuracy | `evaluation/run_evaluation.py` |
| Agent metrics | tool selection + workflow completion + safety | same script |
| System metrics | p50/p95 latency | same script |
| Ablation | k=2 vs k=4 vs k=6 | `evaluation/ablation.py` |
| Design documentation | architecture, RAG, MCP, safety, deployment | `design-and-evaluation.md` |
| AI tooling documentation | usage and responsibility | `ai-tooling.md` |
| Deployment documentation | URL/health/cold-start placeholders | `deployed.md` |
| Demo guidance | 7–10 minute script | `docs/demo-script.md` |
