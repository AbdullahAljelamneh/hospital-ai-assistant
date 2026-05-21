"""Eval Pipeline Runner.

Usage:
    python evals/run_evals.py
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    EVAL_THRESHOLD_ESCALATION,
    EVAL_THRESHOLD_RETRIEVAL,
    EVAL_THRESHOLD_TOOL_SELECTION,
    ESCALATION_KEYWORDS,
    OPENROUTER_API_KEY,
)
from evals.scorers import (
    EvalScore,
    score_escalation,
    score_retrieval,
    score_tool_selection,
)


def load_test_cases() -> list[dict]:
    path = Path(__file__).parent / "test_cases.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_escalation_evals(test_cases: list[dict]) -> list[EvalScore]:
    from openai import OpenAI
    from agent.subagents import TriageSubagent

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
    triage = TriageSubagent(client)
    scores = []

    for tc in test_cases:
        if tc["category"] != "escalation":
            continue

        print(f"  Testing {tc['id']}: {tc['description']}")
        result = triage.classify(tc["input"])
        triage_result = {"urgency": result.urgency.value}
        scores.append(score_escalation(tc, triage_result))

    return scores


def run_retrieval_evals(test_cases: list[dict]) -> list[EvalScore]:
    try:
        from rag.retriever import HospitalRetriever

        retriever = HospitalRetriever()
    except Exception as e:
        print(f"Skipping retrieval evals (run ingest.py first): {e}")
        return []

    scores = []

    for tc in test_cases:
        if tc["category"] != "retrieval":
            continue

        results = retriever.retrieve(tc["input"])
        chunks = [
            {"source": r.source, "section": r.section, "text": r.text} for r in results
        ]

        scores.append(score_retrieval(tc, chunks))

    return scores


def run_tool_selection_evals(test_cases: list[dict]) -> list[EvalScore]:
    scores = []

    dept_keywords = {
        "emergency": ["emergency", "er"],
        "internal_medicine": ["internal", "medicine"],
        "cardiology": ["cardiology", "heart", "cardiac"],
        "orthopedics": ["orthopedic", "bone", "joint", "fracture"],
        "pediatrics": ["pediatric", "children", "child", "kids"],
        "radiology": ["radiology", "xray", "x-ray", "mri", "ct scan"],
        "laboratory": ["lab", "laboratory", "blood test"],
        "pharmacy": ["pharmacy", "medication"],
        "billing": ["billing", "insurance", "payment"],
    }

    for tc in test_cases:
        if tc["category"] != "tool_selection":
            continue

        message_lower = tc["input"].lower()

        detected_dept = None
        for dept_id, keywords in dept_keywords.items():
            if any(kw in message_lower for kw in keywords):
                detected_dept = dept_id
                break

        intent_guess = "UNKNOWN"
        if (
            "book" in message_lower
            or "appointment" in message_lower
            or "schedule" in message_lower
        ):
            intent_guess = "APPOINTMENT"
        elif (
            "wait" in message_lower
            or "queue" in message_lower
            or "how long" in message_lower
        ):
            intent_guess = "QUEUE_STATUS"
        elif (
            "phone" in message_lower
            or "number" in message_lower
            or "where" in message_lower
        ):
            intent_guess = "DEPARTMENT_INFO"
        elif (
            "talk to" in message_lower
            or "real person" in message_lower
            or "human" in message_lower
        ):
            intent_guess = "HUMAN_TRANSFER"

        scores.append(score_tool_selection(tc, intent_guess, None, detected_dept))

    return scores


def print_report(all_scores: list[EvalScore]):
    thresholds = {
        "escalation": EVAL_THRESHOLD_ESCALATION,
        "retrieval": EVAL_THRESHOLD_RETRIEVAL,
        "tool_selection": EVAL_THRESHOLD_TOOL_SELECTION,
    }

    by_category = defaultdict(list)
    for s in all_scores:
        by_category[s.category].append(s)

    print("\n" + "=" * 70)
    print("EVAL RESULTS")
    print("=" * 70)
    print(f"{'ID':<10} {'Category':<16} {'Score':>6} {'Pass':>5}  {'Explanation'}")
    print("-" * 70)

    for s in all_scores:
        status = "PASS" if s.passed else "FAIL"
        print(
            f"{s.test_id:<10} {s.category:<16} {s.score:>5.2f} {status:>5}  {s.explanation}"
        )

    print("\n" + "=" * 70)
    print("CATEGORY SUMMARY")
    print("=" * 70)
    print(
        f"{'Category':<16} {'Avg Score':>10} {'Pass Rate':>10} {'Threshold':>10} {'Status':>8}"
    )
    print("-" * 70)

    for cat, scores in by_category.items():
        avg = sum(s.score for s in scores) / len(scores)
        pass_rate = sum(1 for s in scores if s.passed) / len(scores)
        threshold = thresholds.get(cat, 0.8)
        status = "PASS" if avg >= threshold else "FAIL"
        print(f"{cat:<16} {avg:>9.2f} {pass_rate:>9.0%} {threshold:>9.0%} {status:>8}")

    overall_avg = (
        sum(s.score for s in all_scores) / len(all_scores) if all_scores else 0
    )
    overall_pass = (
        sum(1 for s in all_scores if s.passed) / len(all_scores) if all_scores else 0
    )
    print(
        f"\nOverall: {overall_avg:.2f} avg | {overall_pass:.0%} pass rate | {len(all_scores)} test cases"
    )


def main():
    print("Hospital AI Assistant — Eval Pipeline")
    print("=" * 50)

    test_cases = load_test_cases()
    print(f"Loaded {len(test_cases)} test cases\n")

    all_scores = []

    print("Running escalation evals...")
    all_scores.extend(run_escalation_evals(test_cases))

    print("Running retrieval evals...")
    all_scores.extend(run_retrieval_evals(test_cases))

    print("Running tool selection evals...")
    all_scores.extend(run_tool_selection_evals(test_cases))

    print_report(all_scores)


if __name__ == "__main__":
    main()
