# Evaluation

The project contains **24 evaluation cases** covering:

- straightforward policy questions;
- multi-document questions;
- employee/tool-requiring workflows;
- ambiguous requests requiring clarification;
- out-of-corpus requests;
- action-safety cases.

Run:

```bash
python evaluation/run_evaluation.py
```

The script reports:

- groundedness;
- citation accuracy;
- tool-selection accuracy;
- workflow completion;
- action-safety pass rate;
- p50/p95 latency.

`ablation.py` compares retrieval `k=2`, `k=4` and `k=6`. The chosen production value is `k=4` because it provides enough evidence for multi-policy workflows without unnecessarily expanding the prompt.

The evaluation uses transparent heuristics rather than pretending that keyword matching is a perfect semantic evaluator. For the final submission, keep the generated `results.json` from the environment used for the recorded demo and report the exact run conditions.
