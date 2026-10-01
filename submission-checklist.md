# Final Submission Checklist

## Application
- [ ] Local app starts successfully.
- [ ] `/health` returns `status: ok`.
- [ ] MCP reports all 8 tools.
- [ ] Remote-work demo completes.
- [ ] PTO demo completes.
- [ ] Citations and source snippets appear.
- [ ] Operational trace appears without hidden chain-of-thought.

## Engineering
- [ ] Final RAG index is built during deployment.
- [ ] No secret is committed.
- [ ] `pytest -q` passes.
- [ ] GitHub Actions is green.
- [ ] MCP discovery/call test passes.
- [ ] Evaluation results are generated from the final environment.
- [ ] Ablation output is captured.

## Deployment
- [ ] Render/Railway service is live.
- [ ] Public URL is added to `deployed.md`.
- [ ] Public `/health` URL works.
- [ ] Cold-start note is accurate.

## Documentation
- [ ] `README.md` complete.
- [ ] `design-and-evaluation.md` complete.
- [ ] `ai-tooling.md` complete.
- [ ] `deployed.md` complete.
- [ ] `evaluation/results.json` included after final run.
- [ ] GitHub repo shared with `quantic-grader`.

## Video
- [ ] 7–10 minutes.
- [ ] Voiceover and screen share.
- [ ] Two end-to-end agentic tasks.
- [ ] Tool names shown.
- [ ] Tool arguments shown.
- [ ] Tool outputs shown.
- [ ] Retrieved citations shown.
- [ ] Final behaviour shown.
- [ ] Architecture, deployment, CI/CD and evaluation briefly explained.
