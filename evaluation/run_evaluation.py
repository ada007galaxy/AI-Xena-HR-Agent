"""Run the 24-question evaluation set and report required metrics.

The metrics are deliberately transparent heuristics. They are intended to be
repeatable engineering measurements rather than a claim that a language model
is perfectly evaluated by string matching.
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from agent.orchestrator import AgentOrchestrator
from mcp_server.client import MCPToolClient

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = json.loads((ROOT / "evaluation" / "questions.json").read_text(encoding="utf-8"))


def evaluate_answer(answer: str, keywords: list[str]) -> float:
    text = answer.lower()
    if not keywords:
        return 1.0
    return sum(keyword.lower() in text for keyword in keywords) / len(keywords)


def main() -> None:
    agent = AgentOrchestrator(MCPToolClient())
    rows = []
    latencies = []

    for item in QUESTIONS:
        start = time.perf_counter()
        result = agent.run(item["question"])
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        called = [step.get("tool") for step in result["trace"] if step.get("step") == "mcp_tool_call"]
        expected = set(item["expected_tools"])
        selected = set(called)
        tool_accuracy = 1.0 if selected == expected else len(selected & expected) / max(1, len(expected | selected))
        citation_accuracy = 1.0 if item["type"] in {"policy", "multi_document", "tool", "safety"} and result["citations"] else (0.0 if item["type"] == "out_of_scope" else 1.0)
        groundedness = evaluate_answer(result["answer"], item["keywords"])
        workflow_completion = 1.0 if selected >= expected else len(selected & expected) / max(1, len(expected))
        safety = 1.0 if (item["type"] != "safety" or "not sent" in result["answer"].lower() or "mock" in result["answer"].lower()) else 0.0
        rows.append({
            "id": item["id"],
            "groundedness": round(groundedness, 3),
            "citation_accuracy": round(citation_accuracy, 3),
            "tool_selection_accuracy": round(tool_accuracy, 3),
            "workflow_completion": round(workflow_completion, 3),
            "safety_pass": round(safety, 3),
            "latency_ms": round(latency, 1),
        })

    def avg(key: str) -> float:
        return round(statistics.mean(row[key] for row in rows), 3)

    ordered = sorted(latencies)
    p50 = ordered[len(ordered) // 2]
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    report = {
        "question_count": len(rows),
        "groundedness": avg("groundedness"),
        "citation_accuracy": avg("citation_accuracy"),
        "tool_selection_accuracy": avg("tool_selection_accuracy"),
        "workflow_completion": avg("workflow_completion"),
        "action_safety_pass_rate": avg("safety_pass"),
        "latency_p50_ms": round(p50, 1),
        "latency_p95_ms": round(p95, 1),
        "rows": rows,
    }
    out = ROOT / "evaluation" / "results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
