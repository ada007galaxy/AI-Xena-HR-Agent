# Xena HR Agent

A free-tier-compatible agentic HR policy assistant combining **RAG, MCP tool use, synthetic structured data and an LLM provider**.

The project is designed against the Quantic AI Engineering Techniques and Architectures project requirements.

## Features

- User-friendly HR chat interface.
- 10 synthetic internal policy documents.
- Multi-format ingestion support for Markdown/TXT, HTML and PDF.
- SentenceTransformer semantic embeddings.
- Persistent Chroma vector store with a lightweight fallback.
- Top-k retrieval with citation metadata and snippets.
- MCP server with 8 tools.
- MCP client that discovers tools before calling them.
- Agent planner with OpenRouter support and deterministic fallback.
- Two complete demo workflows: remote work and PTO guidance.
- Visible operational trace showing selected tools, arguments, outputs and citation basis.
- Safe mock actions only; no email is sent and no real HR record is changed.
- `/chat`, `/health` and `/api/demo-tasks` endpoints.
- 24-question evaluation set plus retrieval-k ablation.
- GitHub Actions CI with application and MCP tests.
- Render configuration for free-tier deployment.

## Project structure

```text
AI-Xena-HR-Agent/
├── app.py
├── config.py
├── document_loader.py
├── rag_pipeline.py
├── ingest.py
├── agent/
│   ├── planner.py
│   └── orchestrator.py
├── mcp_server/
│   ├── server.py
│   └── client.py
├── mock_data/
├── policies/
├── evaluation/
├── tests/
├── templates/
├── static/
├── .github/workflows/ci.yml
├── render.yaml
├── Procfile
├── requirements.txt
├── design-and-evaluation.md
├── ai-tooling.md
└── deployed.md
```

## Local setup

Python 3.11 is the recommended runtime for the dependency set used by the CI workflow.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Add the OpenRouter key to `.env` if you want LLM planning/synthesis. The application still has a deterministic fallback for local smoke testing without a key.

Build the RAG index:

```powershell
python ingest.py
```

Run the application:

```powershell
python app.py
```

Open `http://127.0.0.1:5000`.

## Test

```powershell
pytest -q
```

The MCP test discovers the server's tools and calls `lookup_employee_profile` through MCP rather than importing the server function directly.

## API

### `GET /health`

Returns application and MCP status.

### `POST /chat`

Request:

```json
{"message":"EMP001 wants 3 days of PTO next week. Check their balance and the policy."}
```

Response contains:

- `answer`
- `citations`
- `snippets`
- `trace`
- `workflow`
- `escalation`

### `GET /api/demo-tasks`

Returns the two prepared demo prompts.

## Deployment

Render is configured in `render.yaml`. Connect the GitHub repository, set `OPENROUTER_API_KEY` as a secret environment variable and deploy.

After deployment, verify:

https://ai-xena-hr-agent.onrender.com/health

Deployed application:
https://ai-xena-hr-agent.onrender.com

## Evaluation

Run:

```powershell
python evaluation/run_evaluation.py
python evaluation/ablation.py
```

Keep the resulting `evaluation/results.json` from the environment used for the final recorded demonstration.

## Academic integrity

The policies and employee records in this repository are synthetic. AI assistance is documented in `ai-tooling.md`. The student remains responsible for testing, correctness, security and the final submission.

## Submission checklist

Before submitting, confirm:

- [ ] Deployed URL works.
- [ ] `/health` works on the deployed URL.
- [ ] Remote-work demo completes end-to-end.
- [ ] PTO demo completes end-to-end.
- [ ] MCP trace visibly shows tool discovery, arguments and outputs.
- [ ] Citations and source snippets are visible.
- [ ] CI is green on the final commit.
- [ ] `evaluation/results.json` contains the final run.
- [ ] `design-and-evaluation.md` is complete.
- [ ] `ai-tooling.md` is complete.
- [ ] `deployed.md` contains the deployed URL.
- [ ] GitHub repository is shared with `quantic-grader` as required by the brief.
- [ ] Demo video is 7–10 minutes and includes the required two end-to-end tasks.
