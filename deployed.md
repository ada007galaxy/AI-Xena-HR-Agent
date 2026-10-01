# Deployment

**Deployed application URL:** Add the final Render/Railway URL here after deployment.

**Health endpoint:** `<DEPLOYED_URL>/health`

## Free-tier notes

The recommended deployment is a single Render web service. The service runs the Flask web app, agent orchestrator, local MCP server, policy RAG index and synthetic JSON data in one process/container environment.

The service may experience a cold start after inactivity on a free tier. The first request can take longer because Python imports, the MCP subprocess and the local embedding model/index may need to initialise. Warm requests should be faster.

## Environment variables

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `OPENROUTER_BASE_URL`
- `RETRIEVAL_K`

No secret is committed to the repository.
